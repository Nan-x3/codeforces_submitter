#!/usr/bin/env python3
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
"""
Codeforces Submit Tool
======================
Fully automated CLI submission using your Opera GX browser cookies.
No login needed — just make sure you're logged into Codeforces in Opera GX.

Usage:
    py submit.py <filename>       Submit a solution
    py submit.py 112A.py          Example
"""

import re
import json
import time
import urllib.request
import requests
import browser_cookie3

# ─── CONFIG ──────────────────────────────────────────────────────────────────

HANDLE = "nan_x3"
CODEFORCES_URL = "https://codeforces.com"

LANG_MAP = {
    ".py":   70,   # PyPy 3-64
    ".cpp":  89,   # GNU C++20 (64 bit)
    ".c":    43,   # GNU GCC C11
    ".java": 87,   # Java 21
    ".js":   55,   # Node.js
    ".rs":   75,   # Rust 2021
    ".kt":   88,   # Kotlin 1.9
    ".go":   32,   # Go
}

LANG_NAMES = {
    70: "PyPy 3-64",   89: "GNU C++20", 43: "GNU C11",   87: "Java 21",
    55: "Node.js",     75: "Rust 2021", 88: "Kotlin 1.9", 32: "Go",
}

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
    basename = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"^(\d+)([A-Za-z]\d?)$", basename)
    if not match:
        print(f"{C.RED}X Cannot parse contest/problem from '{filename}'{C.RESET}")
        print(f"  Expected: <contestID><problemIndex>.<ext>  e.g. 112A.py")
        sys.exit(1)
    return match.group(1), match.group(2).upper()


def get_lang_id(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in LANG_MAP:
        print(f"{C.RED}X Unsupported extension: {ext}{C.RESET}")
        print(f"  Supported: {', '.join(LANG_MAP.keys())}")
        sys.exit(1)
    return LANG_MAP[ext]


# ─── SESSION ─────────────────────────────────────────────────────────────────

def build_session():
    """
    Build a requests session using cookies from any installed browser.
    Universal solution: works on Windows, macOS, and Linux.
    """
    print(f"{C.CYAN}-> Reading browser cookies...{C.RESET}")

    cookies = {}

    # Define browsers and their custom paths if needed
    browsers = [
        ("Chrome", browser_cookie3.chrome, {}),
        ("Edge", browser_cookie3.edge, {}),
        ("Firefox", browser_cookie3.firefox, {}),
        ("Brave", browser_cookie3.brave, {}),
        ("Opera", browser_cookie3.opera, {}),
    ]

    # Opera GX has a non-standard path on Windows, so we help it out
    if os.name == "nt":
        opera_gx_cookie = os.path.join(os.environ.get("APPDATA", ""), "Opera Software", "Opera GX Stable", "Default", "Network", "Cookies")
        opera_gx_key = os.path.join(os.environ.get("APPDATA", ""), "Opera Software", "Opera GX Stable", "Local State")
        if os.path.exists(opera_gx_cookie) and os.path.exists(opera_gx_key):
            browsers.insert(0, ("Opera GX", browser_cookie3.opera_gx, {"cookie_file": opera_gx_cookie, "key_file": opera_gx_key}))
    else:
        browsers.insert(0, ("Opera GX", browser_cookie3.opera_gx, {}))

    lock_errors = []

    for name, fn, kwargs in browsers:
        try:
            jar = fn(domain_name="codeforces.com", **kwargs)
            for c in jar:
                cookies[c.name] = c.value
            if cookies:
                print(f"  {C.GREEN}OK Found Codeforces cookies in {name}{C.RESET}")
                break
        except PermissionError as e:
            lock_errors.append(name)
        except Exception:
            pass

    if not cookies:
        print(f"{C.RED}X Could not read Codeforces cookies.{C.RESET}")
        if lock_errors:
            print(f"  {C.YELLOW}! The following browsers are currently locking their cookie files:{C.RESET}")
            for b in lock_errors:
                print(f"      - {b}")
            print(f"\n  {C.CYAN}Fix: Please close your browser completely, then try submitting again.{C.RESET}")
        else:
            print(f"  Make sure you are logged into Codeforces in your browser (Chrome, Edge, Firefox, etc).")
        sys.exit(1)

    session = requests.Session()
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".codeforces.com")

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return session





def get_csrf(session, url):
    """Fetch a CSRF token from a Codeforces page."""
    resp = session.get(url, timeout=20)

    if resp.status_code == 403:
        print(f"{C.RED}X Codeforces returned 403 Forbidden.{C.RESET}")
        print(f"  Your Opera GX cf_clearance cookie may be stale.")
        print(f"  Open codeforces.com in Opera GX, browse around, then try again.")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"{C.RED}X HTTP {resp.status_code} from {url}{C.RESET}")
        sys.exit(1)

    for pattern in [
        r"csrf='([a-f0-9]+)'",
        r'name="csrf_token"\s+value="([a-f0-9]+)"',
        r'data-csrf="([a-f0-9]+)"',
    ]:
        m = re.search(pattern, resp.text)
        if m:
            return m.group(1), resp

    # Check if we're actually logged in
    if HANDLE.lower() not in resp.text.lower():
        print(f"{C.RED}X Not logged in on Codeforces.{C.RESET}")
        print(f"  Open Opera GX, go to codeforces.com, log in, then try again.")
        sys.exit(1)

    print(f"{C.RED}X Could not find CSRF token on page.{C.RESET}")
    sys.exit(1)


# ─── SUBMIT ──────────────────────────────────────────────────────────────────

def do_submit(session, contest_id, problem_index, source_code, lang_id):
    submit_url = f"{CODEFORCES_URL}/contest/{contest_id}/submit/{problem_index}"

    print(f"{C.CYAN}-> Fetching submit page...{C.RESET}")
    csrf, _ = get_csrf(session, submit_url)
    print(f"  {C.GREEN}OK Got CSRF token{C.RESET}")

    print(f"{C.CYAN}-> Submitting...{C.RESET}")
    data = {
        "csrf_token":            csrf,
        "action":                "submitSolutionFormSubmitted",
        "contestId":             contest_id,
        "submittedProblemIndex": problem_index,
        "programTypeId":         str(lang_id),
        "source":                source_code,
        "tabSize":               "4",
        "_tta":                  "594",
        "sourceFile":            "",
    }

    resp = session.post(
        f"{submit_url}?csrf_token={csrf}",
        data=data,
        headers={
            "Referer": submit_url,
            "Origin":  CODEFORCES_URL,
        },
        allow_redirects=True,
        timeout=30,
    )

    body = resp.text

    if "You have submitted exactly the same code before" in body:
        print(f"{C.YELLOW}! Already submitted this exact code before.{C.RESET}")
        sys.exit(1)

    # Look for explicit error messages
    err_m = re.search(r'<span class="error[^"]*">([^<]+)</span>', body)
    if err_m:
        print(f"{C.RED}X Submit error: {err_m.group(1).strip()}{C.RESET}")
        sys.exit(1)

    if resp.status_code not in (200, 302):
        print(f"{C.RED}X Submit failed (HTTP {resp.status_code}){C.RESET}")
        sys.exit(1)

    print(f"  {C.GREEN}OK Submitted!{C.RESET}")


# ─── VERDICT ─────────────────────────────────────────────────────────────────

def get_latest_sub_id():
    try:
        url = f"{CODEFORCES_URL}/api/user.status?handle={HANDLE}&from=1&count=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "OK" and data.get("result"):
            return data["result"][0].get("id", 0)
    except Exception:
        pass
    return 0


def poll_verdict(contest_id, old_id):
    api_url = f"{CODEFORCES_URL}/api/user.status?handle={HANDLE}&from=1&count=5"
    print(f"\n{C.CYAN}Waiting for verdict...{C.RESET}", end="", flush=True)

    for _ in range(120):
        time.sleep(2)
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if data.get("status") != "OK":
                print(".", end="", flush=True)
                continue

            for sub in data.get("result", []):
                if sub.get("id", 0) <= old_id:
                    continue
                if str(sub.get("contestId")) != str(contest_id):
                    continue

                verdict = sub.get("verdict", "TESTING")
                if verdict == "TESTING":
                    tc = sub.get("passedTestCount", 0)
                    print(f"\r{C.YELLOW}  Testing... passed {tc} test(s)     {C.RESET}", end="", flush=True)
                    break
                else:
                    return sub
            else:
                print(".", end="", flush=True)

        except Exception:
            print(".", end="", flush=True)

    print(f"\n{C.YELLOW}! Timed out. Check: {CODEFORCES_URL}/profile/{HANDLE}{C.RESET}")
    return None


def display_verdict(sub):
    verdict = sub.get("verdict", "UNKNOWN")
    time_ms = sub.get("timeConsumedMillis", 0)
    mem_mb  = sub.get("memoryConsumedBytes", 0) / (1024 * 1024)
    passed  = sub.get("passedTestCount", 0)
    cid     = sub.get("contestId", "?")
    prob    = sub.get("problem", {})
    pname   = prob.get("name", "?")
    pidx    = prob.get("index", "?")
    sid     = sub.get("id", "?")
    lang    = sub.get("programmingLanguage", "?")
    vc      = C.GREEN if verdict == "OK" else C.RED

    print(f"\n")
    print(f"  {C.BOLD}{'=' * 54}{C.RESET}")
    print(f"  {C.BOLD}  Submission #{sid}{C.RESET}")
    print(f"  {C.BOLD}{'=' * 54}{C.RESET}")
    print(f"    Problem:   {cid}{pidx} - {pname}")
    print(f"    Language:  {lang}")
    print(f"    Verdict:   {vc}{C.BOLD}{verdict.replace('_', ' ')}{C.RESET}")
    if verdict == "OK":
        print(f"    Tests:     {C.GREEN}All {passed} tests passed{C.RESET}")
    else:
        print(f"    Failed on: Test #{passed + 1} (passed {passed})")
    print(f"    Time:      {time_ms} ms")
    print(f"    Memory:    {mem_mb:.2f} MB")
    print(f"  {C.BOLD}{'=' * 54}{C.RESET}")
    print(f"    {CODEFORCES_URL}/contest/{cid}/submission/{sid}")
    print()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"{C.BOLD}Codeforces Submit Tool{C.RESET}")
        print(f"  py submit.py <file>   Submit a solution")
        print(f"  Example: py submit.py 112A.py")
        print(f"\n  Note: Make sure you're logged into Codeforces in Opera GX.")
        sys.exit(0)

    filename = sys.argv[1]
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

    print(f"\n{C.BOLD}{'-' * 54}{C.RESET}")
    print(f"  {C.CYAN}Codeforces Submit{C.RESET}")
    print(f"    File:     {filename}")
    print(f"    Contest:  {contest_id}")
    print(f"    Problem:  {problem_index}")
    print(f"    Language: {LANG_NAMES.get(lang_id, '?')}")
    print(f"    Lines:    {len(source_code.splitlines())}")
    print(f"{C.BOLD}{'-' * 54}{C.RESET}\n")

    # Snapshot latest submission ID before we submit
    old_id = get_latest_sub_id()

    # Build session from Opera GX cookies
    session = build_session()

    # Submit
    do_submit(session, contest_id, problem_index, source_code, lang_id)

    # Poll for verdict
    result = poll_verdict(contest_id, old_id)
    if result:
        display_verdict(result)
        sys.exit(0 if result.get("verdict") == "OK" else 1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
