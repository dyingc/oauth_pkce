import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import getpass
from typing import TypedDict, Annotated

class OAuthTokenResponse(TypedDict):
    access_token: Annotated[str, 'The access token to use for API calls.']
    refresh_token: Annotated[str, 'The refresh token to use for refreshing the access token.']

class OAuthPKCEFlow:
    def __init__(self, oauth_authorize_url, oauth_token_url, client_id, code_verifier, redirect_uri, target_service, oauth_server='localhost', port=8669):
        self.oauth_authorize_url = oauth_authorize_url
        self.oauth_token_url = oauth_token_url
        self.client_id = client_id
        self.code_verifier = code_verifier
        self.redirect_uri = redirect_uri
        self.target_service = target_service
        self.oauth_server = oauth_server
        self.port = port
        self.auth_code = None
        self.httpd = None

    def start_oauth_flow(self)->OAuthTokenResponse:
        self.start_callback_server()
        self.run_selenium_flow()
        self.wait_for_auth_code()
        _, refresh_token = self.exchange_code_for_token()
        token_response: OAuthTokenResponse = self.refresh_token_flow(refresh_token)
        auth_token = self.fetch_internal_access_token(token_response.get('access_token'))
        self.make_final_api_call(auth_token)
        return token_response

    def start_callback_server(self):
        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                parsed_path = urllib.parse.urlparse(handler_self.path)
                if parsed_path.path == '/callback':
                    query_params = urllib.parse.parse_qs(parsed_path.query)
                    if 'code' in query_params:
                        self.auth_code = query_params['code'][0]
                        handler_self.send_response(200)
                        handler_self.end_headers()
                        handler_self.wfile.write(b'Authorization code received. You can close this window.')
                    else:
                        handler_self.send_response(400)
                        handler_self.end_headers()
                        handler_self.wfile.write(b'Missing authorization code.')
                else:
                    pass # Do nothing
                    # handler_self.send_response(404)
                    # handler_self.end_headers()

        server_address = (self.oauth_server, self.port)
        self.httpd = HTTPServer(server_address, OAuthCallbackHandler)
        server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        server_thread.start()

    def run_selenium_flow(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)

        def sso_login(driver, app_url, username, password):
            try:
                driver.get(app_url)
                username_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="idcs-signin-basic-signin-form-username"]'))
                )
                username_input.send_keys(username)

                next_button = driver.find_element(By.XPATH, '//*[@id="idcs-signin-basic-signin-form-submit"]/button')
                next_button.click()

                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="idcs-auth-pwd-input|input"]'))
                )
                password_input.send_keys(password)

                sign_in_button = driver.find_element(By.XPATH, '//*[@id="idcs-mfa-mfa-auth-user-password-submit-button"]/button')
                sign_in_button.click()

                time.sleep(5)
            except Exception as e:
                print(f"Login error: {e}")

        try:
            username = 'c9-security-1_ww@oracle.com'
            password = getpass.getpass("Enter your password: ")
            app_url = "https://cloudsecurity.oraclecorp.com"
            sso_login(driver, app_url, username, password)
            driver.get(self.oauth_authorize_url)
        finally:
            driver.quit()

    def wait_for_auth_code(self, timeout=300):
        total_wait = 0
        wait_interval = 1
        while self.auth_code is None and total_wait < timeout:
            time.sleep(wait_interval)
            total_wait += wait_interval

        if self.auth_code is None:
            raise TimeoutError('Authorization code was not received within the timeout period.')

        self.httpd.shutdown()

    def exchange_code_for_token(self):
        try:
            token_payload = {
                'grant_type': 'authorization_code',
                'code': self.auth_code,
                'client_id': self.client_id,
                'code_verifier': self.code_verifier,
                'redirect_uri': self.redirect_uri
            }
            token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(self.oauth_token_url, data=token_payload, headers=token_headers)
            response.raise_for_status()
            token_data = response.json()
            return token_data.get('access_token'), token_data.get('refresh_token')
        except requests.exceptions.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            raise

    def refresh_token_flow(self, refresh_token)->OAuthTokenResponse:
        try:
            refresh_payload = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': self.client_id
            }
            refresh_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(self.oauth_token_url, data=refresh_payload, headers=refresh_headers)
            response.raise_for_status()
            new_access_token = response.json().get('access_token')
            new_fresh_token = response.json().get('refresh_token')
            if new_access_token is None or new_fresh_token is None:
                raise ValueError('New access token or refresh token is missing.')
            return OAuthTokenResponse(access_token=new_access_token, refresh_token=new_fresh_token)
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing access token: {e}")
            raise

    def fetch_internal_access_token(self, access_token):
        try:
            internal_token_url = f'https://{self.target_service}/20241124/get_internal_group_jwt'
            internal_payload = {
                'accessKey': access_token,
                'expires_in': 3600
            }
            response = requests.post(internal_token_url, json=internal_payload)
            response.raise_for_status()
            return response.json().get('authToken')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching internal access token: {e}")
            raise

    def make_final_api_call(self, auth_token):
        try:
            api_url = f'https://{self.target_service}/20241124/generate_stream'
            headers = {
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }
            user_query = input("Input your question to the Code Assist AI: ")
            payload = {
                "messages": [
                    {"role": "user", "content": "hi"},
                    {"role": "assistant", "content": "Hi! How can I help you today?"},
                    {"role": "user", "content": user_query}
                ],
                "chat": True,
                "modelType": "GENERATION_DEFAULT",
                "parameters": {
                    "maxNewTokens": 16000,
                    "top_p": 0.75,
                    "top_k": 40,
                    "temperature": 0.1,
                    "repetition_penalty": 1.2
                }
            }
            api_response = requests.post(api_url, json=payload, headers=headers, stream=True)
            api_response.raise_for_status()

            # Read the streamed response and get the last 'data' value
            last_data = None
            for line in api_response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data:'):
                        last_data = decoded_line[5:].strip()

            ai_answer = json.loads(last_data).get('generated_text', None)
            if ai_answer:
                print("AI Answer:", ai_answer)
            else:
                print("No AI answer received.")
            # print("Final output:", last_data)


        except Exception as e:
            print(f"Error making final API call: {e}")


# Example usage
if __name__ == "__main__":
    oauth_server = 'idcs-9dc693e80d9b469480d7afe00e743931.identity.oraclecloud.com'
    target_service = 'code-internal.aiservice.us-chicago-1.oci.oraclecloud.com'
    code_challenge = 'ZtNPunH49FD35FWYhT5Tv8I7vRKQJ8uxMaL0_9eHjNA'
    client_id = 'a8331954c0cf48ba99b5dd223a14c6ea'
    redirect_uri = 'http://localhost:8669/callback'
    
    oauth_authorize_url = (
        f'https://{oauth_server}/oauth2/v1/authorize?response_type=code&client_id={client_id}'
        f'&redirect_uri={redirect_uri}&scope=openid%20offline_access'
        f'&code_challenge={code_challenge}&code_challenge_method=S256'
    )
    oauth_token_url = f'https://{oauth_server}/oauth2/v1/token'
    code_verifier = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

    oauth_flow = OAuthPKCEFlow(
        oauth_authorize_url=oauth_authorize_url,
        oauth_token_url=oauth_token_url,
        client_id=client_id,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        target_service=target_service
    )
    token_response: OAuthTokenResponse = oauth_flow.start_oauth_flow()
    # token_response = OAuthTokenResponse(access_token='access', refresh_token='AgAgYmNkNTdiNDkxMzUxNDMxNjgxMDVlMzgzOTdhYmNjMTkIABARnOiO3Ae_RyMovsIfBMSgAAAAQEaqET8ud2Q7Pv9BWaOgTDUxFY85SrkBoe9lC6dkGn9CwvlWidZjK9d2aGM7blmMITr80fYaw-vYGsJkUeRARfI=')
    while [ True ]:
        token_response = oauth_flow.refresh_token_flow(token_response.get('refresh_token'))
        print(f"Current time: {time.ctime()} - New refresh token: {token_response.get('refresh_token')}")
        time.sleep(300)