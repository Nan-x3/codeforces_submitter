# Codeforces Submitter

Python CLI tool for automated submission to [Codeforces](https://codeforces.com) with browser-based form filling and manual CAPTCHA verification.

## Features

- **Automated form filling**: Automatically fills problem code, language, and source code
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Safe CAPTCHA handling**: User completes CAPTCHA manually to avoid anti-bot detection
- **Zero configuration**: Just log in once in your browser, then submit solutions
- **Auto-dependency installation**: Installs Playwright and PyAutoGUI on first run

## Requirements

- Python 3.8+
- Modern browser (Chromium, used by Playwright)
- Logged into Codeforces in your default browser

## Installation

1. Clone this repository:
```bash
git clone <repo-url>
cd codeforces
```

2. Install Python dependencies (auto-installed on first run):
```bash
pip install -r requirements.txt
```

## Usage

### Basic submission
```bash
py submit.py 112A.py
```

### File naming convention
Your solution files must follow this pattern:
```
<contestID><problemIndex>.<extension>
```

Examples:
- `112A.py` → Contest 112, Problem A
- `1900B.cpp` → Contest 1900, Problem B
- `50A.py` → Contest 50, Problem A

### Supported languages

| Extension | Language         | ID |
|-----------|------------------|-----|
| `.py`     | PyPy 3-64        | 70  |
| `.cpp`    | GNU C++20        | 89  |
| `.c`      | GNU C11          | 43  |
| `.java`   | Java 21          | 87  |
| `.js`     | Node.js          | 55  |
| `.rs`     | Rust 2021        | 75  |
| `.kt`     | Kotlin 1.9       | 88  |
| `.go`     | Go               | 32  |

## Workflow

1. **Run**: `py submit.py 112A.py`
2. **Auto-fill**: Script opens browser and fills:
   - Problem code (e.g., 112A)
   - Language selector
   - Source code (via clipboard paste)
3. **Login** (if needed): Log in to Codeforces if the browser detects you're not authenticated
4. **CAPTCHA**: Complete the CAPTCHA verification manually in the browser
5. **Submit**: Script auto-clicks the Submit button
6. **Done**: Check submissions page for verdict

## Example output

```
────────────────────────────────────────────────────

  Codeforces Submit
    File:     112A.py
    Contest:  112
    Problem:  A
    Language: PyPy 3-64
    Lines:    12

────────────────────────────────────────────────────

-> Opening Codeforces...
  OK Page loaded
-> Filling form...
  OK Problem: 112A
  OK Language: PyPy 3-64
-> Pasting code...
  OK Code pasted (345 bytes)

IMPORTANT: Complete the CAPTCHA verification manually in the browser.
  Press Enter when you've completed the CAPTCHA...

-> Clicking Submit...
  OK Submitted!
  OK Submission accepted!

Done!
  Check your submissions: https://codeforces.com/submissions/
```

## How it works

1. **Playwright**: Opens a real browser window (not headless) to the Codeforces submit page
2. **Form filling**: Uses Playwright's DOM selectors to fill form fields
3. **Clipboard paste**: Copies source code to clipboard and pastes it into the textarea
4. **Manual CAPTCHA**: User completes CAPTCHA manually (defeats automated detection)
5. **Auto-submit**: Script clicks the Submit button after CAPTCHA is done

## Why manual CAPTCHA?

Codeforces uses aggressive anti-bot detection including:
- Canvas fingerprinting
- Mouse movement analysis
- Timing analysis
- WebDriver detection

By having the user complete the CAPTCHA manually, we ensure the submission appears as a legitimate human user.

## Troubleshooting

### "File not found"
- Make sure the file exists in your current directory or specify the full path

### "Cannot parse contest/problem"
- Check your filename follows `<contestID><problemIndex>.<extension>` format
- Example: `112A.py` ✓, `a112.py` ✗

### "Could not find form fields"
- Codeforces may have changed their HTML structure
- Open an issue with the error message

### "Not logged in"
- Log in to Codeforces in your default browser first
- The script will pause and prompt you to log in

### Clipboard not working
- On some systems, PowerShell clipboard access may require additional setup
- The script will continue and you can manually paste the code

## License

Personal use. Feel free to adapt for your own setup.

For local testing before submitting, install [cfkit](https://pypi.org/project/cfkit/):

```bash
pip install cfkit
cf parse 112A          # Download test cases
cf run 112A.py         # Test locally against samples
py submit.py 112A.py   # Submit to Codeforces
```

## License

MIT
