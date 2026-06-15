#!/usr/bin/env python3
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
"""
Codeforces Submit Tool (Playwright Edition)
============================================
Submit solutions to Codeforces using a real browser — bypasses Cloudflare.

Usage:
    py submit.py <filename>
    py submit.py 112A.py
    py submit.py --login          (to log in and save session)
"""

import re
import json
import time

# ─── CONFIG ──────────────────────────────────────────────────────────────────

HANDLE = "nan_x3"
CODEFORCES_URL = "https://codeforces.com"
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cf_session.json")

# Codeforces language IDs
LANG_MAP = {
    ".py":   70,   # PyPy 3-64
    ".cpp":  89,   # GNU C++20 (64 bit)
    ".c":    43,   # GNU GCC C11 5.1.0
    ".java": 87,   # Java 21
    ".js":   55,   # Node.js
    ".rs":   75,   # Rust 2021
    ".kt":   88,   # Kotlin 1.9
    ".go":   32,   # Go
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


def get_lang_id(filename):
    """Get Codeforces language ID from file extension"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in LANG_MAP:
        print(f"{C.RED}X Unsupported extension: {ext}{C.RESET}")
        print(f"  Supported: {', '.join(LANG_MAP.keys())}")
        sys.exit(1)
    return LANG_MAP[ext]


def get_lang_name(lang_id):
    """Human-readable name for a language ID"""
    names = {70: "PyPy 3-64", 89: "C++20", 43: "C11", 87: "Java 21",
             55: "Node.js", 75: "Rust", 88: "Kotlin", 32: "Go"}
    return names.get(lang_id, str(lang_id))


# ─── LOGIN ───────────────────────────────────────────────────────────────────

def do_login(playwright):
    """Interactive login — opens a visible browser so you can solve Cloudflare"""
    print(f"\n{C.CYAN}Opening browser for Codeforces login...{C.RESET}")
    print(f"{C.DIM}  A browser window will open. Log in normally.{C.RESET}")
    print(f"{C.DIM}  If there's a Cloudflare challenge, solve it.{C.RESET}")
    print(f"{C.DIM}  The window will close automatically once logged in.{C.RESET}\n")

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(f"{CODEFORCES_URL}/enter", timeout=60000)
    page.wait_for_load_state("domcontentloaded")

    # Pre-fill the handle
    try:
        page.fill("#handleOrEmail", HANDLE)
    except Exception:
        pass

    # Wait for user to log in (check for handle appearing on page)
    print(f"{C.YELLOW}Waiting for you to log in...{C.RESET}")

    for _ in range(300):  # 5 minutes max
        time.sleep(1)
        try:
            content = page.content()
            if f'handle = "{HANDLE}"' in content or f"/{HANDLE}" in page.url:
                break
            # Check if we're on the main page and logged in
            if page.url == f"{CODEFORCES_URL}/" or page.url == f"{CODEFORCES_URL}":
                if HANDLE.lower() in content.lower():
                    break
        except Exception:
            continue
    else:
        print(f"{C.RED}X Login timed out.{C.RESET}")
        browser.close()
        sys.exit(1)

    # Save session cookies
    cookies = context.cookies()
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies, f, indent=2)

    print(f"{C.GREEN}Login successful! Session saved.{C.RESET}")
    browser.close()


# ─── SUBMIT ──────────────────────────────────────────────────────────────────

def do_submit(playwright, filename, contest_id, problem_index, source_code, lang_id):
    """Submit solution using saved session cookies"""

    if not os.path.exists(SESSION_FILE):
        print(f"{C.RED}X No saved session found. Run 'py submit.py --login' first.{C.RESET}")
        sys.exit(1)

    with open(SESSION_FILE, "r") as f:
        cookies = json.load(f)

    # Launch headless browser
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.add_cookies(cookies)
    page = context.new_page()

    # Navigate to submit page
    print(f"{C.CYAN}-> Opening submit page...{C.RESET}")
    submit_url = f"{CODEFORCES_URL}/contest/{contest_id}/submit"
    page.goto(submit_url, timeout=60000)
    page.wait_for_load_state("domcontentloaded")

    # Check if we're logged in
    content = page.content()
    if "Enter" in page.title() or "/enter" in page.url:
        print(f"{C.RED}X Session expired. Run 'py submit.py --login' to re-login.{C.RESET}")
        browser.close()
        sys.exit(1)

    # Check for Cloudflare challenge
    if len(content) < 2000 and ("challenge" in content.lower() or "cloudflare" in content.lower()):
        print(f"{C.YELLOW}Cloudflare challenge detected. Re-login needed.{C.RESET}")
        print(f"Run: py submit.py --login")
        browser.close()
        sys.exit(1)

    print(f"  {C.GREEN}OK Logged in{C.RESET}")

    # Fill the submission form
    print(f"{C.CYAN}-> Filling submission form...{C.RESET}")

    try:
        # Select problem index
        problem_selector = page.locator('select[name="submittedProblemIndex"]')
        if problem_selector.count() > 0:
            problem_selector.select_option(problem_index)

        # Select language
        page.locator('select[name="programTypeId"]').select_option(str(lang_id))

        # Toggle to paste source code instead of file upload
        toggle = page.locator("#toggleEditorCheckbox")
        if toggle.count() > 0 and not toggle.is_checked():
            toggle.click()
            page.wait_for_timeout(500)

        # Try to paste source code into the editor
        # Codeforces uses either a textarea or an ACE/CodeMirror editor
        source_textarea = page.locator("#sourceCodeTextarea")
        if source_textarea.count() > 0:
            source_textarea.fill(source_code)
        else:
            # Try file upload as fallback
            file_input = page.locator('input[name="sourceFile"]')
            if file_input.count() > 0:
                # Write source to a temp file and upload
                temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp_submit" + os.path.splitext(filename)[1])
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(source_code)
                file_input.set_input_files(temp_file)
                # Clean up later
            else:
                print(f"{C.RED}X Could not find source code input on page.{C.RESET}")
                browser.close()
                sys.exit(1)

    except Exception as e:
        print(f"{C.RED}X Error filling form: {e}{C.RESET}")
        browser.close()
        sys.exit(1)

    print(f"  {C.GREEN}OK Form filled{C.RESET}")

    # Click submit
    print(f"{C.CYAN}-> Submitting...{C.RESET}")
    try:
        submit_btn = page.locator('input.submit[type="submit"], input[value="Submit"]')
        submit_btn.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"{C.RED}X Error clicking submit: {e}{C.RESET}")
        browser.close()
        sys.exit(1)

    # Check result
    current_url = page.url
    page_content = page.content()

    # Check for error messages
    if "You have submitted exactly the same code before" in page_content:
        print(f"{C.YELLOW}! You already submitted this exact code.{C.RESET}")
        browser.close()
        sys.exit(1)

    error_el = page.locator("span.error")
    if error_el.count() > 0:
        err_text = error_el.first.inner_text()
        if err_text.strip():
            print(f"{C.RED}X Submit error: {err_text}{C.RESET}")
            browser.close()
            sys.exit(1)

    if "/my" in current_url or "/status" in current_url:
        print(f"  {C.GREEN}OK Solution submitted!{C.RESET}")
    else:
        print(f"  {C.YELLOW}! Submission may have succeeded (URL: {current_url}){C.RESET}")

    # Save updated cookies
    cookies = context.cookies()
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies, f, indent=2)

    browser.close()

    # Clean up temp file
    temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp_submit" + os.path.splitext(filename)[1])
    if os.path.exists(temp_file):
        os.remove(temp_file)

    return True


# ─── VERDICT ─────────────────────────────────────────────────────────────────

def poll_verdict(contest_id):
    """Poll the Codeforces API for the latest submission verdict"""
    import urllib.request

    api_url = f"{CODEFORCES_URL}/api/user.status?handle={HANDLE}&from=1&count=5"
    print(f"\n{C.CYAN}Waiting for verdict...{C.RESET}", end="", flush=True)

    for attempt in range(60):
        time.sleep(2)
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if data.get("status") != "OK" or not data.get("result"):
                print(".", end="", flush=True)
                continue

            # Find submission for this contest
            for sub in data["result"]:
                if str(sub.get("contestId")) != str(contest_id):
                    continue

                verdict = sub.get("verdict", "TESTING")

                if verdict == "TESTING":
                    tc = sub.get("passedTestCount", 0)
                    print(f"\r{C.YELLOW}Testing... passed {tc} test(s)     {C.RESET}", end="", flush=True)
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
    """Display the verdict nicely"""
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
    vc = C.GREEN if is_ok else C.RED if verdict != "TESTING" else C.YELLOW

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
    from playwright.sync_api import sync_playwright

    if len(sys.argv) < 2:
        print(f"{C.BOLD}Codeforces Submit Tool{C.RESET}")
        print(f"  py submit.py <filename>   Submit a solution")
        print(f"  py submit.py --login      Log in to Codeforces")
        sys.exit(0)

    with sync_playwright() as pw:

        # Login mode
        if sys.argv[1] == "--login":
            do_login(pw)
            return

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

        print(f"\n{C.BOLD}{'-' * 56}{C.RESET}")
        print(f"  {C.CYAN}Codeforces Submit{C.RESET}")
        print(f"    File:     {filename}")
        print(f"    Contest:  {contest_id}")
        print(f"    Problem:  {problem_index}")
        print(f"    Language: {get_lang_name(lang_id)}")
        print(f"    Lines:    {len(source_code.splitlines())}")
        print(f"{C.BOLD}{'-' * 56}{C.RESET}")

        success = do_submit(pw, filename, contest_id, problem_index, source_code, lang_id)

        if success:
            result = poll_verdict(contest_id)
            if result:
                display_verdict(result)
                sys.exit(0 if result.get("verdict") == "OK" else 1)
            else:
                sys.exit(1)


if __name__ == "__main__":
    main()
