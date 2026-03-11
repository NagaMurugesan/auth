import os
import urllib.parse
import httpx
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

OKTA_DOMAIN = os.environ.get("OKTA_DOMAIN")
CLIENT_ID = os.environ.get("OKTA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("OKTA_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")

def get_login_url(state=""):
    """Generates the Okta authorization URL."""
    if not all([OKTA_DOMAIN, CLIENT_ID, REDIRECT_URI]):
        return None

    # Use the default authorization server by appending /oauth2/default
    # Depending on your Okta setup, you might not have a custom authorization server.
    # If using the Org authorization server, it would be OKTA_DOMAIN/oauth2/v1/authorize
    # Standard practice is to use the 'default' custom authorization server.
    # Adjust this path if necessary for your Okta org.
    auth_endpoint = f"{OKTA_DOMAIN.rstrip('/')}/oauth2/default/v1/authorize"

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        # Requesting email or preferred_username for Windows Logon ID depending on your Okta mapping
        "scope": "openid profile email", 
        "redirect_uri": REDIRECT_URI,
        "state": state,
        # 'prompt=login' forces the user to re-authenticate at Okta, 
        # bypassing any existing active Okta SSO sessions.
        "prompt": "login"
    }

    url_parts = list(urllib.parse.urlparse(auth_endpoint))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)

    return urllib.parse.urlunparse(url_parts)


def exchange_code(code: str) -> dict | None:
    """Exchanges an authorization code for tokens."""
    if not all([OKTA_DOMAIN, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        return None

    token_endpoint = f"{OKTA_DOMAIN.rstrip('/')}/oauth2/default/v1/token"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    
    try:
        response = httpx.post(token_endpoint, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Save the id_token in our local session so we can use it for logout later
        import streamlit as st
        st.session_state["id_token"] = token_data.get("id_token")
        
        return token_data
    except Exception as e:
        print(f"Error exchanging code: {e}")
        return None


def get_user_info(id_token: str) -> dict | None:
    """Extracts user information from the decoded ID token.
       Okta's Desktop SSO puts the user's Active Directory UPN or 
       samAccountName into the token claims depending on configuration.
    """
    try:
        # We are skipping signature verification here for simplicity in the Streamlit app demo,
        # but in production you MUST securely verify the token signature using Okta's JWKS.
        claims = jwt.get_unverified_claims(id_token)
        return claims
    except Exception as e:
        print(f"Error decoding ID token: {e}")
        return None


def get_logout_url(id_token: str = None) -> str:
    """Generates the Okta logout URL to terminate the Okta session."""
    if not all([OKTA_DOMAIN, REDIRECT_URI]):
        return None
        
    logout_endpoint = f"{OKTA_DOMAIN.rstrip('/')}/oauth2/default/v1/logout"
    
    params = {
        "post_logout_redirect_uri": REDIRECT_URI
    }
    
    if id_token:
        params["id_token_hint"] = id_token
        
    url_parts = list(urllib.parse.urlparse(logout_endpoint))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)

    return urllib.parse.urlunparse(url_parts)
