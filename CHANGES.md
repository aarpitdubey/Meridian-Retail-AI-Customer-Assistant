# MeridianRetail-AI-Chat-Assistant-upgraded

Improved the terminal-first experience while preserving the existing policy, case data, API integration, offline demo, and JSON output contract. The CLI now validates inputs, supports listing cases and output formatting, handles failures safely, and avoids exposing secrets; setup and documentation are clearer and safer.

## What is new
- Implemented complete CLI workflow with case listing, offline mode, simulated timeout, human-review-safe output, and JSON or readable terminal output.
- Added robust case and demo-file validation plus safe error messages and exit codes.
- Made API responses and request failures more defensive without printing credentials.
- Updated setup to hide API-key input and write the environment file with restrictive permissions where supported.
- Documented terminal usage, offline operation, output formats, and safety behavior.

## Files
- changed: MeridianRetail-AI-Chat-Assistant/src/meridian/app.py
- changed: MeridianRetail-AI-Chat-Assistant/src/meridian/euri_client.py
- changed: MeridianRetail-AI-Chat-Assistant/setup_env.py
- changed: MeridianRetail-AI-Chat-Assistant/README.md
