# OAuth PKCE Flow for Code Assist AI

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Code Structure](#code-structure)
7. [Detailed Workflow](#detailed-workflow)
8. [Security Considerations](#security-considerations)
9. [Error Handling](#error-handling)
10. [Future Improvements](#future-improvements)
11. [Contributing](#contributing)
12. [License](#license)

## Introduction

This Python script implements an OAuth 2.0 Authorization Code flow with Proof Key for Code Exchange (PKCE) to authenticate and interact with a Code Assist AI service. It automates the process of obtaining and refreshing OAuth tokens, and demonstrates how to make API calls to the AI service.

The main purpose of this script is to provide a secure and automated way to authenticate with an OAuth server, obtain necessary tokens, and interact with an AI service that requires these tokens for authorization.

## Features

- Implements OAuth 2.0 Authorization Code flow with PKCE
- Automated SSO login using Selenium WebDriver
- Local callback server to receive the authorization code
- Token exchange and refresh mechanisms
- Interaction with a Code Assist AI service
- Continuous token refresh functionality

## Requirements

- Python 3.7+
- Selenium WebDriver
- ChromeDriver (compatible with your Chrome version)
- `requests` library
- `urllib3` library

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/dyingc/oauth-pkce.git
   cd oauth-pkce
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Download and install ChromeDriver:
   - Visit the [ChromeDriver downloads page](https://sites.google.com/a/chromium.org/chromedriver/downloads)
   - Download the version that matches your Chrome installation
   - Add the ChromeDriver executable to your system PATH

## Usage

1. Update the configuration variables in the `__main__` section of the script:
   - `oauth_server`
   - `target_service`
   - `code_challenge`
   - `client_id`
   - `redirect_uri`
   - `code_verifier`

2. Run the script:
   ```
   python oauth_pkce.py
   ```

3. Follow the prompts to enter your username and password for SSO login.

4. After successful authentication, you can input your question to the Code Assist AI.

5. The script will continuously refresh the token every 5 minutes.

## Code Structure

The main class `OAuthPKCEFlow` encapsulates the entire OAuth flow and AI service interaction. Key methods include:

- `start_oauth_flow()`: Orchestrates the entire OAuth process
- `start_callback_server()`: Starts a local server to receive the authorization code
- `run_selenium_flow()`: Automates the SSO login process
- `exchange_code_for_token()`: Exchanges the authorization code for access and refresh tokens
- `refresh_token_flow()`: Refreshes the access token using the refresh token
- `fetch_internal_access_token()`: Obtains an internal access token for API calls
- `make_final_api_call()`: Interacts with the Code Assist AI service

## Detailed Workflow

1. The script starts a local HTTP server to receive the OAuth callback.
2. It then initiates a headless Chrome browser session to perform SSO login.
3. After successful login, it waits for the authorization code from the callback server.
4. The authorization code is exchanged for access and refresh tokens.
5. An internal access token is obtained using the access token.
6. The script makes an API call to the Code Assist AI service with the user's query.
7. Finally, it enters a loop to refresh the token every 5 minutes.

## Security Considerations

- The script uses PKCE to enhance security for public clients.
- Passwords are not stored and are securely input using `getpass`.
- Tokens are not persisted between runs of the script.
- The script uses HTTPS for all network communications.

## Error Handling

The script includes basic error handling for network requests and authentication flows. However, in a production environment, more robust error handling and logging should be implemented.

## Future Improvements

- Implement more robust error handling and logging
- Add support for different OAuth providers
- Improve the user interface, possibly with a GUI
- Implement token storage for persistence between runs
- Add unit tests and integration tests

## Contributing

Contributions to improve the script are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature-name`)
3. Make your changes and commit them (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature-name`)
5. Create a new Pull Request

## License

MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
