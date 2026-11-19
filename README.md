# Meridian Retail Customer Agent

A terminal-first classroom demo that drafts customer-support replies from `policy.md` and `cases.json`. Every result is for human review only: the tool cannot approve refunds, send messages, or change records.

## Setup

sh
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt


No API key is needed for the prerecorded demo. For live drafting, configure a key interactively (the key input is hidden):

sh
python setup_env.py


The script writes `.env`; do not commit it. Euri defaults to model `euri-auto` and base URL `https://api.euron.one/api/v1/euri`.

## Run in the terminal

sh
python app.py --list-cases
python app.py --case C1 --offline-demo        # no network or key required
python app.py --case C1 --offline-demo --format text
python app.py --case C1                       # calls Euri when configured
python app.py --case C1 --simulate-timeout


JSON is the default output and is suitable for piping or scripting. Use `--format text` for a readable summary. Unknown cases and invalid input produce a clear error on stderr. An unavailable result exits with status 1; successful results exit with status 0.

## Test

sh
pytest -q


## Files

| File | Purpose |
| --- | --- |
| `app.py` | Root command-line entry point |
| `policy.md` | Policy lines used for every draft |
| `cases.json` | Synthetic cases C1, C2, and C3 |
| `demo_outputs.json` | Prerecorded synthetic outputs for offline use |
| `setup_env.py` | Hidden-input, local environment setup |
| `src/meridian/app.py` | CLI, input checks, output, and safe fallback handling |
| `src/meridian/euri_client.py` | Isolated Euri API client |
| `src/meridian/config.py` | Project paths and environment defaults |

## Safety and privacy

- `needs_human_review` is always `true`; a draft is not an approval or sent message.
- Offline demo and timeout simulation make no network requests.
- API errors return an unavailable result rather than inventing a draft.
- API keys are never printed, and provider response bodies are not echoed in errors.
