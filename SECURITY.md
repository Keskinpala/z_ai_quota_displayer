# Security Policy

## Supported Versions

Security updates are provided for the latest stable release.


| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it directly by opening a GitHub Issue.

**How to report:**
1. **Open an Issue:** Navigate to the [Issues tab](https://github.com/Keskinpala/z_ai_quota_displayer/issues) and describe the vulnerability.
2. **Response:** You can expect a response within 48 hours.
3. **Process:** Once the vulnerability is confirmed, a patch will be released and you will be credited.

## Important Note on API Tokens
Z.ai Monitor stores your API token locally on your machine (`%APPDATA%/ZaiMonitor/config.json`).
- **Never** share this configuration file with others.
- Ensure your token is hidden or blurred when taking **screenshots**.
- The application **does not** send your token to any third-party servers; it only communicates directly with the official Z.ai API endpoints.
