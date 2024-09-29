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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import getpass
import time


def oauth_flow(oauth_authorize_url, oauth_token_url, client_id, code_verifier, redirect_uri, target_service, oauth_server):
    # Start the HTTP server to listen for the callback
    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urllib.parse.urlparse(self.path)
            if parsed_path.path == '/callback':
                query_params = urllib.parse.parse_qs(parsed_path.query)
                if 'code' in query_params:
                    self.server.auth_code = query_params['code'][0]
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'Authorization code received. You can close this window.')
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Missing authorization code.')
            else:
                self.send_response(404)
                self.end_headers()

    server_address = ('', 8669)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)

    # Start the server in a new thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Start Selenium browser
    try:
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Remove this option if you want to see the browser
        # chromedriver download: https://googlechromelabs.github.io/chrome-for-testing/ and put the executable to /usr/local/lib/node_modules/chromedriver/lib/chromedriver/chromedriver
        driver = webdriver.Chrome(options=chrome_options)

        # Login using selenium script
        def login(app_url: str, username: str, password: str):
            # Open the specified app_url
            driver.get(app_url)
            
            try:
                # Wait until the Username input box appears and input username
                username_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="idcs-signin-basic-signin-form-username"]'))
                )
                username_input.send_keys(username)

                # Click the "Next" button
                next_button = driver.find_element(By.XPATH, '//*[@id="idcs-signin-basic-signin-form-submit"]/button')
                next_button.click()

                # Wait until the password input box appears and input the password
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="idcs-auth-pwd-input|input"]'))
                )
                password_input.send_keys(password)

                # Click on the "Sign In" button
                sign_in_button = driver.find_element(By.XPATH, '//*[@id="idcs-mfa-mfa-auth-user-password-submit-button"]/button')
                sign_in_button.click()

                # Optional: Wait a few seconds to ensure the login is processed
                time.sleep(5)  # Adjust the time as needed
            except Exception as e:
                print(f"An error occurred: {e}")

        # Main part of the script
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Uncomment this if you want to run in headless mode
            driver = webdriver.Chrome(options=chrome_options)

            # Get username and password from the user console input
            username = 'c9-security-1_ww@oracle.com'
            print(f"You username is: {username}")
            password = getpass.getpass("Enter your password: ")

            # Perform login using the provided username and password
            app_url = "https://cloudsecurity.oraclecorp.com" 
            login(app_url, username, password)

            # Navigate to the OAuth2 authorize URL
            driver.get(oauth_authorize_url)



        except Exception as e:
            print(f"An error occurred during setup: {e}")

        # Wait until the authorization code is received or timeout
        max_wait_time = 300  # seconds
        wait_interval = 1  # seconds
        total_wait = 0
        while not hasattr(httpd, 'auth_code') and total_wait < max_wait_time:
            time.sleep(wait_interval)
            total_wait += wait_interval

        if not hasattr(httpd, 'auth_code'):
            raise Exception('Authorization code was not received within the timeout period.')

        auth_code = httpd.auth_code

    except Exception as e:
        print(f"An error occurred during the OAuth flow: {e}")
        driver.quit()
        httpd.shutdown()
        return

    finally:
        driver.quit()
        httpd.shutdown()

    # Exchange authorization code for access token and refresh token
    try:
        token_payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'client_id': client_id,
            'code_verifier': code_verifier,
            'redirect_uri': redirect_uri
        }
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        token_response = requests.post(oauth_token_url, data=token_payload, headers=token_headers)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')

    except Exception as e:
        print(f"An error occurred while exchanging the authorization code: {e}")
        return

    # Refresh the access token using the refresh token
    try:
        refresh_payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id
        }
        refresh_response = requests.post(oauth_token_url, data=refresh_payload, headers=token_headers)
        refresh_response.raise_for_status()
        refresh_data = refresh_response.json()
        refreshed_access_token = refresh_data.get('access_token')

    except Exception as e:
        print(f"An error occurred while refreshing the access token: {e}")
        return

    # Fetch internal access token
    try:
        internal_token_url = f'https://{target_service}/20241124/get_internal_group_jwt'
        internal_payload = {
            'accessKey': refreshed_access_token,
            'expires_in': 3600
        }
        internal_response = requests.post(internal_token_url, json=internal_payload)
        internal_response.raise_for_status()
        internal_data = internal_response.json()
        auth_token = internal_data.get('authToken')

    except Exception as e:
        print(f"An error occurred while fetching the internal access token: {e}")
        return

    # Make the final API call
    try:
        api_url = f'https://{target_service}/20241124/generate_stream'
        api_headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
        user_query = input("Input your question to the Code Assist AI: ")
        api_payload = {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "Hi! How can I help you today? If you have any questions or need assistance, feel free to ask."},
                {"role": "user", "content": f"{user_query}"}
            ],
            "chat": True,
            "modelType": "GENERATION_DEFAULT",
            "usageType": "GENERAL_QUESTION",
            "parameters": {
                "maxNewTokens": 16000,
                "top_p": 0.75,
                "top_k": 40,
                "temperature": 0.1,
                "repetition_penalty": 1.2
            }
        }
        api_response = requests.post(api_url, json=api_payload, headers=api_headers, stream=True)
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
        print(f"An error occurred while making the final API call: {e}")
        return


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

    oauth_flow(oauth_authorize_url, oauth_token_url, client_id, code_verifier, redirect_uri, target_service, oauth_server)