# app.py
import streamlit as st
import requests
from pathlib import Path
import yaml
import json

# Page configuration
st.set_page_config(
    page_title="Algo Trading Login",
    page_icon="🔐",
    layout="centered"
)

# Custom CSS for styling
st.markdown("""
    <style>
        .main {
            padding-top: 2rem;
        }
        .stButton>button {
            width: 100%;
            margin-top: 1rem;
        }
        .success-msg {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            color: #155724;
            margin: 1rem 0;
        }
        .error-msg {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            color: #721c24;
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None

class UpstoxAuth:
    def __init__(self):
        self.api_key = st.secrets["UPSTOX_API_KEY"]
        self.api_secret = st.secrets["UPSTOX_API_SECRET"]
        self.redirect_uri = "http://localhost:8501/callback"
        self.base_url = "https://api.upstox.com/v2"

    def get_login_url(self):
        return f"{self.base_url}/login/authorization/dialog?response_type=code&client_id={self.api_key}&redirect_uri={self.redirect_uri}"

    def get_access_token(self, auth_code):
        try:
            response = requests.post(
                f"{self.base_url}/login/authorization/token",
                data={
                    "code": auth_code,
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                st.error(f"Error: {response.json().get('message', 'Failed to get access token')}")
                return None
        except Exception as e:
            st.error(f"Error during authentication: {str(e)}")
            return None

    def get_user_profile(self, access_token):
        try:
            response = requests.get(
                f"{self.base_url}/user/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error fetching profile: {str(e)}")
            return None

def save_token(token):
    """Save token securely"""
    token_file = Path(".streamlit/token.yaml")
    token_file.parent.mkdir(exist_ok=True)
    with open(token_file, "w") as f:
        yaml.dump({"access_token": token}, f)

def load_token():
    """Load saved token"""
    token_file = Path(".streamlit/token.yaml")
    if token_file.exists():
        with open(token_file, "r") as f:
            data = yaml.safe_load(f)
            return data.get("access_token")
    return None

def main():
    auth = UpstoxAuth()
    
    # Center-aligned title with emoji
    st.markdown("<h1 style='text-align: center;'>🤖 Algo Trading</h1>", unsafe_allow_html=True)
    
    # Handle callback from Upstox
    query_params = st.experimental_get_query_params()
    if "code" in query_params:
        auth_code = query_params["code"][0]
        with st.spinner("Authenticating..."):
            token = auth.get_access_token(auth_code)
            if token:
                st.session_state.access_token = token
                save_token(token)
                # Clear URL parameters
                st.experimental_set_query_params()
                st.rerun()

    # Check for existing token
    if not st.session_state.access_token:
        token = load_token()
        if token:
            st.session_state.access_token = token

    # Show login interface or user profile
    if st.session_state.access_token:
        if not st.session_state.user_profile:
            with st.spinner("Loading profile..."):
                profile = auth.get_user_profile(st.session_state.access_token)
                if profile:
                    st.session_state.user_profile = profile
                else:
                    st.session_state.access_token = None
                    st.rerun()

        if st.session_state.user_profile:
            # Display user profile in a clean card-like container
            st.markdown("""
                <div style='
                    background-color: #f8f9fa;
                    padding: 1.5rem;
                    border-radius: 0.5rem;
                    margin: 1rem 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                '>
                    <h3 style='margin-bottom: 1rem; color: #333;'>Welcome! 👋</h3>
                    <p style='margin-bottom: 0.5rem;'><strong>Name:</strong> {name}</p>
                    <p style='margin-bottom: 0.5rem;'><strong>Email:</strong> {email}</p>
                    <p style='margin-bottom: 0.5rem;'><strong>User ID:</strong> {user_id}</p>
                </div>
            """.format(**st.session_state.user_profile), unsafe_allow_html=True)

            if st.button("Proceed to Trading Dashboard →"):
                # Here you'll redirect to the trading dashboard
                st.switch_page("pages/dashboard.py")

            if st.button("Logout"):
                st.session_state.access_token = None
                st.session_state.user_profile = None
                Path(".streamlit/token.yaml").unlink(missing_ok=True)
                st.rerun()
    else:
        # Show login button
        st.markdown("""
            <div style='text-align: center; margin: 2rem 0;'>
                <p style='color: #666; margin-bottom: 2rem;'>
                    Login with your Upstox account to start trading
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Login with Upstox"):
            login_url = auth.get_login_url()
            st.markdown(f'<meta http-equiv="refresh" content="0;url={login_url}">', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
