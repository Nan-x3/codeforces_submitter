#!/usr/bin/env python3
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
"""
Codeforces Submit Tool
======================
Submit solutions to Codeforces from the terminal.

Usage:
    py submit.py <filename>       Submit a solution
    py submit.py 112A.py          Example

How it works:
    1. Copies your source code to clipboard
    2. Opens the Codeforces submit page in your browser
    3. You paste the code and click Submit
    4. The tool auto-polls for the verdict and shows results
"""

import re
import json
import time
import subprocess
import webbrowser
import urllib.request

# ─── CONFIG ──────────────────────────────────────────────────────────────────

HANDLE = "nan_x3"
CODEFORCES_URL = "https://codeforces.com"

# Codeforces language names (for display only)
LANG_NAMES = {
    ".py":   "PyPy 3-64 (or Python 3)",
    ".cpp":  "GNU C++20 (64 bit)",
    ".c":    "GNU GCC C11",
    ".java": "Java 21",
    ".js":   "Node.js",
    ".rs":   "Rust 2021",
    ".kt":   "Kotlin 1.9",
    ".go":   "Go",
}

# Terminal colours
class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def parse_filename(filename):
    """Extract contest ID and problem index from '112A.py' -> ('112', 'A')"""
    basename = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"^(\d+)([A-Za-z]\d?)$", basename)
    if not match:
        print(f"{C.RED}X Cannot parse contest/problem from '{filename}'{C.RESET}")
        print(f"  Expected: <contestID><problemIndex>.<ext>  e.g. 112A.py")
        sys.exit(1)
    return match.group(1), match.group(2).upper()


def get_lang_name(filename):
    """Get language name from file extension"""
    ext = os.path.splitext(filename)[1].lower()
    return LANG_NAMES.get(ext, "Unknown")


def copy_to_clipboard(text):
    """Copy text to Windows clipboard"""
    process = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
    process.communicate(text.encode("utf-16-le"))


def get_latest_submission_id():
    """Get the ID of the latest submission before we submit"""
    try:
        api_url = f"{CODEFORCES_URL}/api/user.status?handle={HANDLE}&from=1&count=1"
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "OK" and data.get("result"):
            return data["result"][0].get("id", 0)
    except Exception:
        pass
    return 0


# ─── VERDICT ─────────────────────────────────────────────────────────────────

VERDICT_COLORS = {
    "OK": C.GREEN, "ACCEPTED": C.GREEN,
    "WRONG_ANSWER": C.RED, "TIME_LIMIT_EXCEEDED": C.RED,
    "MEMORY_LIMIT_EXCEEDED": C.RED, "RUNTIME_ERROR": C.RED,
    "COMPILATION_ERROR": C.RED, "PRESENTATION_ERROR": C.RED,
    "IDLENESS_LIMIT_EXCEEDED": C.RED, "CHALLENGED": C.RED,
    "TESTING": C.YELLOW,
}


def poll_verdict(contest_id, old_submission_id):
    """Poll the Codeforces API until a new submission verdict appears"""
    api_url = f"{CODEFORCES_URL}/api/user.status?handle={HANDLE}&from=1&count=5"

    print(f"\n{C.CYAN}Waiting for new submission...{C.RESET}", end="", flush=True)

    for attempt in range(120):  # Max 4 minutes
        time.sleep(2)
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if data.get("status") != "OK" or not data.get("result"):
                print(".", end="", flush=True)
                continue

            for sub in data["result"]:
                sub_id = sub.get("id", 0)

                # Skip old submissions
                if sub_id <= old_submission_id:
                    continue

                # Check if it's for the right contest
                if str(sub.get("contestId")) != str(contest_id):
                    continue

                verdict = sub.get("verdict", "TESTING")

                if verdict == "TESTING":
                    tc = sub.get("passedTestCount", 0)
                    print(f"\r{C.YELLOW}  Testing... passed {tc} test(s)        {C.RESET}", end="", flush=True)
                    break
                else:
                    return sub

            else:
                print(".", end="", flush=True)

        except Exception:
            print(".", end="", flush=True)
            continue

    print(f"\n{C.YELLOW}! Timed out. Check on the website.{C.RESET}")
    return None


def display_verdict(sub):
    """Display the verdict"""
    verdict = sub.get("verdict", "UNKNOWN")
    time_ms = sub.get("timeConsumedMillis", 0)
    mem_bytes = sub.get("memoryConsumedBytes", 0)
    mem_mb = mem_bytes / (1024 * 1024)
    passed = sub.get("passedTestCount", 0)
    cid = sub.get("contestId", "?")
    prob = sub.get("problem", {})
    pname = prob.get("name", "?")
    pidx = prob.get("index", "?")
    sid = sub.get("id", "?")
    lang = sub.get("programmingLanguage", "?")

    is_ok = verdict == "OK"
    vc = VERDICT_COLORS.get(verdict, C.YELLOW)

    print(f"\n")
    print(f"  {C.BOLD}{'=' * 56}{C.RESET}")
    print(f"  {C.BOLD}  Submission #{sid}{C.RESET}")
    print(f"  {C.BOLD}{'=' * 56}{C.RESET}")
    print(f"    Problem:   {cid}{pidx} - {pname}")
    print(f"    Language:  {lang}")
    print(f"    Verdict:   {vc}{C.BOLD}{verdict.replace('_', ' ')}{C.RESET}")

    if is_ok:
        print(f"    Tests:     {C.GREEN}All {passed} tests passed{C.RESET}")
    else:
        print(f"    Failed on: Test #{passed + 1} (passed {passed})")

    print(f"    Time:      {time_ms} ms")
    print(f"    Memory:    {mem_mb:.2f} MB")
    print(f"  {C.BOLD}{'=' * 56}{C.RESET}")
    print(f"    {CODEFORCES_URL}/contest/{cid}/submission/{sid}")
    print()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"{C.BOLD}Codeforces Submit Tool{C.RESET}")
        print(f"  py submit.py <filename>   Submit a solution")
        print(f"  Example: py submit.py 112A.py")
        sys.exit(0)

    filename = sys.argv[1]

    if not os.path.exists(filename):
        print(f"{C.RED}X File not found: {filename}{C.RESET}")
        sys.exit(1)

    contest_id, problem_index = parse_filename(filename)
    lang_name = get_lang_name(filename)

    with open(filename, "r", encoding="utf-8") as f:
        source_code = f.read()

    if not source_code.strip():
        print(f"{C.RED}X File is empty!{C.RESET}")
        sys.exit(1)

    # ─── Show info ───
    print(f"\n{C.BOLD}{'-' * 56}{C.RESET}")
    print(f"  {C.CYAN}Codeforces Submit{C.RESET}")
    print(f"    File:     {filename}")
    print(f"    Contest:  {contest_id}")
    print(f"    Problem:  {problem_index}")
    print(f"    Language: {lang_name}")
    print(f"    Lines:    {len(source_code.splitlines())}")
    print(f"{C.BOLD}{'-' * 56}{C.RESET}")

    # ─── Get current latest submission ID (to detect new ones) ───
    print(f"\n{C.CYAN}-> Checking current submissions...{C.RESET}")
    old_id = get_latest_submission_id()
    print(f"  {C.GREEN}OK{C.RESET}")

    # ─── Copy to clipboard ───
    print(f"{C.CYAN}-> Copying source code to clipboard...{C.RESET}")
    copy_to_clipboard(source_code)
    print(f"  {C.GREEN}OK Code copied!{C.RESET}")

    # ─── Open submit page ───
    submit_url = f"{CODEFORCES_URL}/contest/{contest_id}/submit/problem/{problem_index}"
    print(f"{C.CYAN}-> Opening submit page in your browser...{C.RESET}")
    webbrowser.open(submit_url)

    # ─── Instructions ───
    print(f"\n  {C.BOLD}{C.YELLOW}Now in your browser:{C.RESET}")
    print(f"  {C.BOLD}  1.{C.RESET} Select language: {C.CYAN}{lang_name}{C.RESET}")
    print(f"  {C.BOLD}  2.{C.RESET} Click in the code editor")
    print(f"  {C.BOLD}  3.{C.RESET} Press {C.BOLD}Ctrl+A{C.RESET} then {C.BOLD}Ctrl+V{C.RESET} to paste your code")
    print(f"  {C.BOLD}  4.{C.RESET} Click {C.BOLD}Submit{C.RESET}")

    # ─── Poll for verdict ───
    result = poll_verdict(contest_id, old_id)

    if result:
        display_verdict(result)
        sys.exit(0 if result.get("verdict") == "OK" else 1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
