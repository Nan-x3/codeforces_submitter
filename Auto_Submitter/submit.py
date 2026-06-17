#!/usr/bin/env python3
"""
Codeforces Submit Tool
======================
Automated CLI submission tool for Codeforces using native GUI automation.

Workflow:
  1. Load or prompt for user's Codeforces handle.
  2. Query Codeforces API for baseline submission ID.
  3. Copy source code to clipboard.
  4. Open default browser to Codeforces submit page.
  5. Wait for page to load.
  6. Auto-fill problem code, language, and paste code via PyAutoGUI.
  7. Wait in background for a new submission on the API.
  8. Once detected (meaning user clicked submit), send Ctrl+W to close tab.
  9. Poll API until verdict is complete and display results.
"""

import sys
import os
import re
import subprocess
import time
import webbrowser
import json
import urllib.request
import urllib.error

try:
    import pyautogui
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "pyautogui"])
    import pyautogui

CODEFORCES_URL = "https://codeforces.com/problemset/submit"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

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


def get_handle():
    """Load handle from config or prompt the user."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if "handle" in data:
                    return data["handle"]
        except Exception:
            pass

    print(f"\n{C.CYAN}First time setup!{C.RESET}")
    handle = input(f"Enter your Codeforces handle: ").strip()
    if not handle:
        print(f"{C.RED}X Handle cannot be empty.{C.RESET}")
        sys.exit(1)
        
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"handle": handle}, f)
        print(f"  {C.GREEN}OK Saved to {CONFIG_FILE}{C.RESET}\n")
    except Exception as e:
        print(f"{C.YELLOW}! Could not save config: {e}{C.RESET}\n")
        
    return handle


def api_get_latest_submission(handle):
    """Fetch the latest submission from the Codeforces API."""
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        data = json.loads(resp)
        if data.get("status") == "OK" and data.get("result"):
            return data["result"][0]
        return None
    except urllib.error.HTTPError as e:
        # 400 Bad Request usually means the handle doesn't exist or has 0 submissions
        return None
    except Exception:
        return None


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
    """Copy text to system clipboard preserving newlines and unicode."""
    import base64
    try:
        b64 = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        ps_cmd = f"$bytes = [Convert]::FromBase64String('{b64}'); $text = [Text.Encoding]::UTF8.GetString($bytes); Set-Clipboard -Value $text"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, timeout=5)
        return True
    except Exception:
        # Fallback to clip.exe
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=5)
            return p.returncode == 0
        except Exception:
            return False


def submit_solution(filename):
    """Submit a solution using Native GUI automation."""
    handle = get_handle()
    
    if not os.path.exists(filename):
        print(f"{C.RED}X File not found: {filename}{C.RESET}")
        sys.exit(1)

    contest_id, problem_index = parse_filename(filename)
    lang_id = get_lang_id(filename)
    problem_code = f"{contest_id}{problem_index}"
    lang_name = LANG_NAMES.get(lang_id, "")

    with open(filename, "r", encoding="utf-8") as f:
        source_code = f.read()

    if not source_code.strip():
        print(f"{C.RED}X File is empty!{C.RESET}")
        sys.exit(1)

    print(f"\n{C.BOLD}{'-' * 60}{C.RESET}")
    print(f"  {C.CYAN}Codeforces Submit{C.RESET}")
    print(f"    User:     {handle}")
    print(f"    File:     {filename}")
    print(f"    Problem:  {problem_code}")
    print(f"    Language: {lang_name}")
    print(f"    Lines:    {len(source_code.splitlines())}")
    print(f"{C.BOLD}{'-' * 60}{C.RESET}\n")

    # Get baseline submission ID to detect when a new one appears
    print(f"{C.CYAN}-> Checking API baseline...{C.RESET}")
    baseline_sub = api_get_latest_submission(handle)
    baseline_id = baseline_sub["id"] if baseline_sub else 0

    print(f"{C.CYAN}-> Copying code to clipboard...{C.RESET}")
    if not copy_to_clipboard(source_code):
        print(f"  {C.RED}X Could not copy to clipboard{C.RESET}")
        sys.exit(1)
    print(f"  {C.GREEN}OK Code copied ({len(source_code)} bytes){C.RESET}")

    print(f"{C.CYAN}-> Opening default browser...{C.RESET}")
    webbrowser.open(CODEFORCES_URL)
    
    print(f"  {C.YELLOW}Waiting for page to load (detecting window title)... DO NOT touch the mouse/keyboard!{C.RESET}")
    
    # Smart wait: observe the active window title to know when Codeforces is actually loaded
    import ctypes
    timeout = 20
    start_time = time.time()
    page_loaded = False
    
    while time.time() - start_time < timeout:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value if buf.value else ""
            
            # Codeforces submit page title is usually "Submit Code - Codeforces"
            if "Submit Code" in title:
                page_loaded = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not page_loaded:
        print(f"  {C.YELLOW}! Could not detect page load after 20s, attempting to type anyway...{C.RESET}")
    
    # Wait 1.5 extra seconds for the DOM to fully render and the cursor to auto-focus into the box
    time.sleep(1.5)

    print(f"{C.CYAN}-> Auto-filling form...{C.RESET}")
    
    # 1. Type problem code (cursor is automatically here when page loads)
    pyautogui.typewrite(problem_code, interval=0.05)
    time.sleep(0.2)
    
    # 2. Tab to Language selector
    pyautogui.press('tab')
    time.sleep(0.2)
    
    # 3. Type language to select it in the dropdown
    if lang_name:
        pyautogui.typewrite(lang_name[:5], interval=0.05)
        time.sleep(0.2)
        
    # 4. Tab to reach the Source Code textarea 
    # (CodeMirror traps the Tab key, so we can safely overshoot the number of tabs to guarantee we reach it)
    pyautogui.press('tab', presses=4, interval=0.1)
    time.sleep(0.2)
    
    # 5. Clear any stray tabs/characters that were typed into the editor, then Paste
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('backspace')
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    print(f"  {C.GREEN}OK Code pasted!{C.RESET}")
    
    print(f"\n{C.YELLOW}IMPORTANT: Complete the CAPTCHA and click SUBMIT manually.{C.RESET}")
    print(f"{C.CYAN}-> Waiting for you to submit...{C.RESET}")
    
    # Wait for the user to submit
    new_sub = None
    while True:
        time.sleep(2)
        latest = api_get_latest_submission(handle)
        if latest and latest["id"] > baseline_id:
            new_sub = latest
            break

    # Detect the submit and close the tab!
    print(f"  {C.GREEN}OK Submission detected! Closing browser tab...{C.RESET}")
    pyautogui.hotkey('ctrl', 'w')
    
    print(f"\n{C.BOLD}--- Live Verdict ---{C.RESET}")
    
    # Poll for verdict
    last_msg = ""
    while True:
        verdict = new_sub.get("verdict")
        if verdict and verdict != "TESTING":
            break
            
        passedTestCount = new_sub.get("passedTestCount", 0)
        msg = f"  Running on test {passedTestCount + 1}..."
        
        if msg != last_msg:
            print(msg)
            last_msg = msg
            
        time.sleep(2)
        latest = api_get_latest_submission(handle)
        if latest and latest["id"] == new_sub["id"]:
            new_sub = latest

    # Final verdict
    verdict = new_sub.get("verdict")
    time_ms = new_sub.get("timeConsumedMillis", 0)
    mem_kb = new_sub.get("memoryConsumedBytes", 0) // 1024
    
    if verdict == "OK":
        print(f"\n  {C.GREEN}{C.BOLD}✅ ACCEPTED{C.RESET} ({time_ms}ms, {mem_kb}KB)")
    elif verdict == "WRONG_ANSWER":
        print(f"\n  {C.RED}{C.BOLD}❌ WRONG ANSWER{C.RESET} on test {new_sub.get('passedTestCount', 0) + 1} ({time_ms}ms, {mem_kb}KB)")
    elif verdict == "TIME_LIMIT_EXCEEDED":
        print(f"\n  {C.YELLOW}{C.BOLD}⏱️ TIME LIMIT EXCEEDED{C.RESET} on test {new_sub.get('passedTestCount', 0) + 1} ({time_ms}ms, {mem_kb}KB)")
    elif verdict == "COMPILATION_ERROR":
        print(f"\n  {C.YELLOW}{C.BOLD}⚠️ COMPILATION ERROR{C.RESET}")
    else:
        print(f"\n  {C.YELLOW}{C.BOLD}⚠️ {verdict}{C.RESET} on test {new_sub.get('passedTestCount', 0) + 1} ({time_ms}ms, {mem_kb}KB)")


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
