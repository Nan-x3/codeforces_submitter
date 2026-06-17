#!/usr/bin/env python3
"""
Codeforces Submit Tool
======================
Automated CLI submission tool for Codeforces.

Workflow:
  1. Open browser to Codeforces submit page
  2. Check if logged in (user logs in if needed)
  3. Auto-fill problem code, language, and code
  4. User completes CAPTCHA manually (for safety)
  5. Auto-click Submit

Usage:
  py submit.py 112A.py          Submit solution
  py submit.py --help           Show help
"""

import sys
import os
import re
import subprocess
import time
from pathlib import Path

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    print("Installing playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "playwright", "pyautogui"])
    # Also install browser binaries
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright, expect

try:
    import pyautogui
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "pyautogui"])
    import pyautogui

CODEFORCES_URL = "https://codeforces.com/problemset/submit"

LANG_MAP = {
    ".py": "70",    # PyPy 3-64
    ".cpp": "89",   # GNU C++20
    ".c": "43",     # GNU C11
    ".java": "87",  # Java 21
    ".js": "55",    # Node.js
    ".rs": "75",    # Rust 2021
    ".kt": "88",    # Kotlin 1.9
    ".go": "32",    # Go
}

LANG_NAMES = {
    "70": "PyPy 3-64", "89": "GNU C++20", "43": "GNU C11", "87": "Java 21",
    "55": "Node.js", "75": "Rust 2021", "88": "Kotlin 1.9", "32": "Go",
}

class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


def parse_filename(filename):
    """Extract contest ID and problem index from filename."""
    basename = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"^(\d+)([A-Za-z]\d?)$", basename)
    if not match:
        print(f"{C.RED}X Cannot parse contest/problem from '{filename}'{C.RESET}")
        print(f"  Expected: <contestID><problemIndex>.<ext>  (e.g., 112A.py)")
        sys.exit(1)
    return match.group(1), match.group(2).upper()


def get_lang_id(filename):
    """Get language ID from file extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in LANG_MAP:
        print(f"{C.RED}X Unsupported extension: {ext}{C.RESET}")
        print(f"  Supported: {', '.join(LANG_MAP.keys())}")
        sys.exit(1)
    return LANG_MAP[ext]


def copy_to_clipboard(text):
    """Copy text to system clipboard."""
    try:
        p = subprocess.Popen(
            ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetText($input)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate(input=text.encode("utf-8"), timeout=5)
        return True
    except Exception:
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=5)
            return p.returncode == 0
        except Exception:
            return False


def is_logged_in(page):
    """Check if user is logged into Codeforces."""
    try:
        # Look for logout link (present only if logged in)
        logout_link = page.query_selector('a[href*="logout"]')
        return logout_link is not None
    except Exception:
        return False


def submit_solution(filename):
    """Submit a solution using Playwright."""
    if not os.path.exists(filename):
        print(f"{C.RED}X File not found: {filename}{C.RESET}")
        sys.exit(1)

    contest_id, problem_index = parse_filename(filename)
    lang_id = get_lang_id(filename)

    with open(filename, "r", encoding="utf-8") as f:
        source_code = f.read()

    if not source_code.strip():
        print(f"{C.RED}X File is empty!{C.RESET}")
        sys.exit(1)

    print(f"\n{C.BOLD}{'-' * 60}{C.RESET}")
    print(f"  {C.CYAN}Codeforces Submit{C.RESET}")
    print(f"    File:     {filename}")
    print(f"    Contest:  {contest_id}")
    print(f"    Problem:  {problem_index}")
    print(f"    Language: {LANG_NAMES.get(lang_id, '?')}")
    print(f"    Lines:    {len(source_code.splitlines())}")
    print(f"{C.BOLD}{'-' * 60}{C.RESET}\n")

    print(f"{C.CYAN}-> Opening Codeforces...{C.RESET}")

    with sync_playwright() as p:
        # Try to open with Opera GX first (user's default), fall back to Chromium
        browser = None
        try:
            # Try Opera GX
            browser = p.chromium.launch(headless=False, channel="opera")
        except Exception:
            try:
                # Fall back to Chromium
                browser = p.chromium.launch(headless=False)
            except Exception as e:
                print(f"{C.RED}X Could not launch browser: {e}{C.RESET}")
                sys.exit(1)
        
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            # Navigate to submit page
            page.goto(CODEFORCES_URL)
            print(f"  {C.GREEN}OK Page loaded{C.RESET}")

            # Check if logged in
            time.sleep(2)
            if not is_logged_in(page):
                print(f"{C.YELLOW}! Not logged in to Codeforces.{C.RESET}")
                input(f"  {C.CYAN}Please log in in the browser, then press Enter...{C.RESET}")
                time.sleep(1)

            # Fill contest and problem code
            print(f"{C.CYAN}-> Filling form...{C.RESET}")
            
            # Find the problem code field
            problem_code = f"{contest_id}{problem_index}"
            problem_input = page.query_selector('input[name="submittedProblemCode"]')
            if problem_input:
                problem_input.fill(problem_code)
                print(f"  {C.GREEN}OK Problem: {problem_code}{C.RESET}")
            else:
                print(f"  {C.YELLOW}! Could not find problem code field{C.RESET}")

            # Select language
            lang_select = page.query_selector('select[name="programTypeId"]')
            if lang_select:
                lang_select.select_option(lang_id)
                print(f"  {C.GREEN}OK Language: {LANG_NAMES.get(lang_id, lang_id)}{C.RESET}")
            else:
                print(f"  {C.YELLOW}! Could not find language selector{C.RESET}")

            # Fill source code using clipboard (safer than PyAutoGUI typing)
            print(f"{C.CYAN}-> Pasting code...{C.RESET}")
            if copy_to_clipboard(source_code):
                source_textarea = page.query_selector('textarea[name="source"]')
                if source_textarea:
                    source_textarea.click()
                    time.sleep(0.5)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Control+V")
                    time.sleep(1)
                    print(f"  {C.GREEN}OK Code pasted ({len(source_code)} bytes){C.RESET}")
                else:
                    print(f"  {C.RED}X Could not find source code textarea{C.RESET}")
                    sys.exit(1)
            else:
                print(f"  {C.RED}X Could not copy to clipboard{C.RESET}")
                sys.exit(1)

            # Wait for user to complete CAPTCHA
            print(f"\n{C.YELLOW}IMPORTANT: Complete the CAPTCHA verification manually in the browser.{C.RESET}")
            input(f"  {C.CYAN}Press Enter when you've completed the CAPTCHA...{C.RESET}\n")

            # Click Submit button
            print(f"{C.CYAN}-> Clicking Submit...{C.RESET}")
            submit_button = page.query_selector('button:has-text("Submit")')
            if not submit_button:
                submit_button = page.query_selector('input[type="submit"]')
            
            if submit_button:
                submit_button.click()
                print(f"  {C.GREEN}OK Submitted!{C.RESET}")
                time.sleep(2)
                
                # Wait for submission to process
                try:
                    page.wait_for_url("**/contest/**", timeout=10000)
                    print(f"  {C.GREEN}OK Submission accepted!{C.RESET}")
                except Exception:
                    print(f"  {C.YELLOW}! Submission processing...{C.RESET}")
            else:
                print(f"  {C.RED}X Could not find Submit button{C.RESET}")
                sys.exit(1)

            print(f"\n{C.GREEN}Done!{C.RESET}")
            print(f"  Check your submissions: https://codeforces.com/submissions/")

        except Exception as e:
            print(f"{C.RED}X Error: {e}{C.RESET}")
            sys.exit(1)
        finally:
            browser.close()


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        print(f"{C.BOLD}Codeforces Submit Tool{C.RESET}")
        print(f"  py submit.py <file>    Submit a solution")
        print(f"  Example: py submit.py 112A.py")
        print(f"\nFile naming: <contestID><problemIndex>.<extension>")
        print(f"  Supported extensions: {', '.join(LANG_MAP.keys())}")
        sys.exit(0)

    filename = sys.argv[1]
    submit_solution(filename)


if __name__ == "__main__":
    main()
