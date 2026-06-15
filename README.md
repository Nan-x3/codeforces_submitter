# Codeforces Submitter

A Python CLI tool for submitting solutions to [Codeforces](https://codeforces.com) directly from your terminal. Uses Playwright (a real Chromium browser) to bypass Cloudflare protection.

## Features

- **Submit solutions** from the command line with a single command
- **Auto-detects cookies** from your browser — no manual setup
- **Supports Opera GX, Chrome, Edge, Firefox** — uses whichever you're logged into
- **Polls verdicts** in real-time with timing and memory stats
- **Works on any Windows PC** — just clone, install deps, and run

## Requirements

- Python 3.8+
- One of: **Opera GX**, Chrome, Edge, or Firefox — logged into Codeforces

## Setup

```bash
pip install requests browser-cookie3 pycryptodomex
```

That's it. No login command, no config file. Just make sure you're logged into Codeforces in your browser.

## Usage

### Login (one-time)
```bash
py submit.py --login
```
A Chromium window opens. Log in normally (handle any Cloudflare challenges). Session cookies are saved automatically.

### Submit a solution
```bash
py submit.py 112A.py
```

The filename must follow the pattern `<contestID><problemIndex>.<ext>`:
- `112A.py` → Contest 112, Problem A
- `1900B.cpp` → Contest 1900, Problem B
- `263A.py` → Contest 263, Problem A

### Example output
```
--------------------------------------------------------
  Codeforces Submit
    File:     112A.py
    Contest:  112
    Problem:  A
    Language: PyPy 3-64
    Lines:    9
--------------------------------------------------------
-> Opening submit page...
  OK Logged in
-> Filling submission form...
  OK Form filled
-> Submitting...
  OK Solution submitted!

Waiting for verdict...
  ========================================================
    Submission #376812345
  ========================================================
    Problem:   112A - Petya and Strings
    Language:  PyPy 3-64
    Verdict:   OK
    Tests:     All 30 tests passed
    Time:      92 ms
    Memory:    0.10 MB
  ========================================================
```

## Supported Languages

| Extension | Codeforces Language      |
|-----------|--------------------------|
| `.py`     | PyPy 3-64                |
| `.cpp`    | GNU C++20 (64 bit)       |
| `.c`      | GNU GCC C11              |
| `.java`   | Java 21                  |
| `.js`     | Node.js                  |
| `.rs`     | Rust 2021                |
| `.kt`     | Kotlin 1.9               |
| `.go`     | Go                       |

## File naming convention

Name your solution files as `<contestID><problemIndex>.<extension>`:
```
112A.py       # Contest 112, Problem A
1900B.cpp     # Contest 1900, Problem B  
50A.py        # Contest 50, Problem A
```

## Session management

- Session cookies are stored in `cf_session.json` (git-ignored)
- If your session expires, run `py submit.py --login` again
- The tool automatically refreshes cookies on each submission

## How it works

1. **Login**: Opens Playwright's bundled Chromium browser for manual login. Saves session cookies to `cf_session.json`.
2. **Submit**: Launches a headless browser with saved cookies, navigates to the submit page, fills the form, and clicks submit.
3. **Verdict**: Polls the Codeforces API (`/api/user.status`) every 2 seconds until the verdict is available.

## Why Playwright?

Codeforces uses Cloudflare protection that blocks automated HTTP requests (even with libraries like `requests` or `cloudscraper`). Playwright uses a real Chromium browser that handles Cloudflare challenges naturally.

## Local Testing (with cfkit)

For local testing before submitting, install [cfkit](https://pypi.org/project/cfkit/):

```bash
pip install cfkit
cf parse 112A          # Download test cases
cf run 112A.py         # Test locally against samples
py submit.py 112A.py   # Submit to Codeforces
```

## License

MIT
