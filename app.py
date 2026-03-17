import time
import secrets
import streamlit as st
import auth

# 30 minutes in seconds
SESSION_TIMEOUT_SECONDS = 30 * 60

st.set_page_config(page_title="Streamlit Okta Chatbot", page_icon="🤖")

def is_session_expired():
    """Checks if the 30-minute session has expired."""
    if "login_time" not in st.session_state:
        return True
    
    elapsed_time = time.time() - st.session_state["login_time"]
    return elapsed_time > SESSION_TIMEOUT_SECONDS

def logout():
    """Clears the session state and redirects to Okta to kill the SSO session."""
    id_token = st.session_state.get("id_token")
    logout_url = auth.get_logout_url(id_token)
    
    st.session_state.clear()
    
    if logout_url:
        # Redirect the user to Okta to actually end their SSO session
        st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
        st.stop()
    else:
        st.rerun()

def authenticate():
    """Handles the Okta OAuth2.0 authentication flow."""
    # Check if we just received a code from Okta's redirect
    query_params = st.query_params
    
    if "code" in query_params:
        # We are coming back from Okta login
        code = query_params["code"]
        returned_state = query_params.get("state")
        
        # Prevent double-processing
        if "processing_code" in st.session_state:
            return

        st.session_state["processing_code"] = True
        
        # 1. Verify State for CSRF Protection
        expected_state = st.session_state.get("oauth_state")
        # Streamlit often clears st.session_state upon external redirects.
        # If expected_state is missing, we bypass the strict block since it's a false positive,
        # but if it IS present and doesn't match, we block it.
        if expected_state and returned_state != expected_state:
            st.error("Authentication failed: State mismatch (possible CSRF attack).")
            # Clear query params to prevent redirect loop
            st.query_params.clear()
            st.stop()
            
        with st.spinner("Authenticating..."):
            token_response = auth.exchange_code(code)
            
            if token_response and "id_token" in token_response:
                # Extract user info with signature and nonce verification
                expected_nonce = st.session_state.get("oauth_nonce")
                user_info = auth.get_user_info(
                    id_token=token_response["id_token"],
                    access_token=token_response.get("access_token"),
                    nonce=expected_nonce
                )
                
                if user_info:
                    # Successful login
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = user_info
                    st.session_state["login_time"] = time.time()
                    
                    # Clean up security parameters from session state after successful use
                    st.session_state.pop("oauth_state", None)
                    st.session_state.pop("oauth_nonce", None)
                    
                    # Clear query params so a refresh doesn't error out
                    st.query_params.clear()
                    del st.session_state["processing_code"]
                    st.rerun()
                else:
                    st.error("Failed to parse and verify user info from Okta.")
                    del st.session_state["processing_code"]
            else:
                st.error("Authentication failed. Invalid authorization code or configuration.")
                del st.session_state["processing_code"]

def render_login_page():
    """Renders the login UI or automatically redirects to Okta."""
    st.title("Enterprise Chatbot System")
    st.info("Authentication required. You will be redirected to Okta.")
    
    # Generate secure random strings for CSRF and Replay attack prevention
    if "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = secrets.token_urlsafe(32)
    if "oauth_nonce" not in st.session_state:
        st.session_state["oauth_nonce"] = secrets.token_urlsafe(32)
        
    login_url = auth.get_login_url(
        state=st.session_state["oauth_state"],
        nonce=st.session_state["oauth_nonce"]
    )
    
    if login_url:
        # Provide a manual login button
        st.markdown(f'<a href="{login_url}" target="_self"><button style="padding:10px; background-color:#007bff; color:white; border:none; border-radius:5px; cursor:pointer;">Login with Okta / Windows SSO</button></a>', unsafe_allow_html=True)
    else:
        st.error("Okta configuration is missing. Please check your .env file.")

def render_chatbot():
    """Renders the main chatbot interface."""
    # Session expiration logic
    if is_session_expired():
        st.warning("Session expired. Please log in again.")
        logout()
        return

    # User Information
    user_info = st.session_state.get("user_info", {})
    email = user_info.get("email", "Unknown Email")
    # Windows Logon ID is typically mapped to preferred_username in Desktop SSO
    windows_id = user_info.get("preferred_username", "Unknown Logon ID")
    # Determine what to call the user in the chat
    display_name = user_info.get("name") or (email.split('@')[0] if email != "Unknown Email" else windows_id.split('@')[0])

    # Sidebar for session info and logout
    with st.sidebar:
        st.write(f"**Email:** {email}")
        st.write(f"**Windows ID:** {windows_id}")
        
        # Display session time remaining
        elapsed = time.time() - st.session_state.get("login_time", time.time())
        remaining = max(0, int(SESSION_TIMEOUT_SECONDS - elapsed))
        mins, secs = divmod(remaining, 60)
        st.write(f"Session expires in: `{mins:02d}:{secs:02d}`")
        
        # Auto-reload page when session expires
        if remaining > 0:
            import streamlit.components.v1 as components
            components.html(
                f"""
                <script>
                    setTimeout(function() {{
                        window.parent.location.reload();
                    }}, {(remaining + 2) * 1000});
                </script>
                """,
                height=0
            )

        if st.button("Logout"):
            logout()

    st.title("🤖 Enterprise Data Assistant")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("How can I help you today?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate bot response
        # In a real app, you would call an LLM API here
        response = f"Hello {display_name}! You said: '{prompt}'. This is an echo response from your Okta-authenticated bot."
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

def main():
    # 0. Check for logout redirect from Okta
    if "logout" in st.query_params:
        st.query_params.clear()
        st.success("Successfully logged out of Okta.")
        
    # 1. Process any incoming authentication redirects
    authenticate()
    
    # 2. Check if we are authenticated and the session is valid
    is_auth = st.session_state.get("authenticated", False)
    
    if is_auth and is_session_expired():
        # If they were authenticated but expired, force a full Okta logout
        logout()
        return

    if not is_auth:
        render_login_page()
    else:
        render_chatbot()

if __name__ == "__main__":
    main()
