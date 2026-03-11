# Streamlit Chatbot with Okta OAuth2.0 Verification Walkthrough

The application has been successfully created. Here is what has been built and how to run your local tests.

## Changes Made
1. **[requirements.txt](file:///d:/murugesan.nagarajan/project/OAuth2/requirements.txt)**: Added `streamlit`, `httpx`, `python-jose`, and `python-dotenv` dependencies.
2. **[.env.template](file:///d:/murugesan.nagarajan/project/OAuth2/.env.template)**: A template file you must copy to `.env` containing Okta settings.
3. **[auth.py](file:///d:/murugesan.nagarajan/project/OAuth2/auth.py)**: A helper module that handles generating the login URL, exchanging the authorization code, and decoding the token to extract the Windows Logon ID / username.
4. **[app.py](file:///d:/murugesan.nagarajan/project/OAuth2/app.py)**: The main Streamlit UI containing:
   - Logic that inspects `st.session_state` and the URL parameters (`st.query_params`) to determine if a user is logged in.
   - An auto-redirect loop that immediately bounces anonymous users to your Okta domain via client-side Javascript.
   - Session enforcement calculating `time.time() - st.session_state.login_time > 1800` (30 minutes) and logging the user out if exceeded.
   - An Enterprise Chatbot UI with `st.chat_message` displaying who the user logged in as.

## Next Steps for Validation

Because this application relies on your specific Okta tenant and credentials (for Windows Integrated Desktop SSO), you will need to run the application locally to test the flow:

### 1. Setup Environment
```powershell
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy [.env.template](file:///d:/murugesan.nagarajan/project/OAuth2/.env.template) to `.env` and fill in your Okta parameters:
```env
OKTA_DOMAIN=https://dev-XXXXXX.okta.com
OKTA_CLIENT_ID=your_client_id
OKTA_CLIENT_SECRET=your_client_secret
REDIRECT_URI=http://localhost:8501/
```
*Make sure `http://localhost:8501/` is registered as an allowed Redirect URI in your Okta application configuration!*

### 3. Run the App
```powershell
streamlit run app.py
```

### Expected Flow:
1. When you hit `http://localhost:8501/`, the app will see you have no session.
2. It will automatically redirect your browser to Okta.
3. Okta will either auto-log you in via Desktop SSO (Windows Logon validation) or prompt you, then redirect back to `http://localhost:8501/?code=...`.
4. Streamlit will exchange the code silently and update the URL to hide it.
5. You will see the chatbot UI displaying your login ID in the sidebar.
6. The sidebar will tell you exactly how many minutes remain out of 30. If you leave it idle for 30 minutes, you will be redirected to log in again.
