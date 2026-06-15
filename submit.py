#!/usr/bin/env python3
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
"""
Codeforces Submit Tool
======================
Fully automated CLI submission to Codeforces.

Usage:
    py submit.py --login          One-time login (opens browser window)
    py submit.py <filename>       Submit silently, get verdict in terminal
    py submit.py 112A.py          Example
"""

import re
import json
import time
import urllib.request

# ─── CONFIG ──────────────────────────────────────────────────────────────────

HANDLE = "nan_x3"
CODEFORCES_URL = "https://codeforces.com"

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(SCRIPT_DIR, ".cf_browser_profile")

# Codeforces language IDs
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
    70: "PyPy 3-64", 89: "GNU C++20", 43: "GNU C11", 87: "Java 21",
    55: "Node.js",   75: "Rust 2021", 88: "Kotlin",  32: "Go",
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
    basename = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"^(\d+)([A-Za-z]\d?)$", basename)
    if not match:
        print(f"{C.RED}X Cannot parse contest/problem from '{filename}'{C.RESET}")
        print(f"  Expected format: <contestID><problemIndex>.<ext>  e.g. 112A.py")
        sys.exit(1)
    return match.group(1), match.group(2).upper()


def get_lang_id(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in LANG_MAP:
        print(f"{C.RED}X Unsupported extension: {ext}{C.RESET}")
        print(f"  Supported: {', '.join(LANG_MAP.keys())}")
        sys.exit(1)
    return LANG_MAP[ext]


def make_context(playwright, headless=True):
    """Launch a persistent browser context (shares cookies/profile across runs)"""
    return playwright.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
        ],
        ignore_default_args=["--enable-automation"],
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.7778.96 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )


def stealth_page(page):
    """Inject JS to hide automation signals"""
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3] });
        window.chrome = { runtime: {} };
    """)
    return page


# ─── LOGIN ───────────────────────────────────────────────────────────────────

def do_login(playwright):
    """Open a visible browser for one-time login. Saves session to profile dir."""
    print(f"\n{C.CYAN}Opening browser for login...{C.RESET}")
    print(f"  1. Wait for the browser to load")
    print(f"  2. Solve the Cloudflare checkbox if it appears")
    print(f"  3. Log in with your Codeforces credentials")
    print(f"  4. This window will close automatically\n")

    context = make_context(playwright, headless=False)
    page = stealth_page(context.new_page())

    # Navigate to login page
    page.goto(f"{CODEFORCES_URL}/enter", timeout=60000)
    page.wait_for_load_state("domcontentloaded")

    print(f"{C.YELLOW}Waiting for you to log in... (5 min timeout){C.RESET}")

    logged_in = False
    for _ in range(300):
        time.sleep(1)
        try:
            content = page.content()
            url = page.url
            # Detect successful login
            if f'handle = "{HANDLE}"' in content:
                logged_in = True
                break
            if "codeforces.com" in url and "/enter" not in url and "/login" not in url:
                if HANDLE.lower() in content.lower():
                    logged_in = True
                    break
        except Exception:
            continue

    if not logged_in:
        print(f"{C.RED}X Login timed out.{C.RESET}")
        context.close()
        sys.exit(1)

    print(f"{C.GREEN}Logged in! Saving session...{C.RESET}")

    # Navigate home to refresh all cookies (incl. cf_clearance)
    page.goto(CODEFORCES_URL, timeout=30000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    context.close()
    print(f"{C.GREEN}Session saved to profile. You can now submit with: py submit.py <file>{C.RESET}\n")


# ─── SUBMIT ──────────────────────────────────────────────────────────────────

def do_submit(playwright, filename, contest_id, problem_index, source_code, lang_id):
    """Submit silently using the saved browser profile."""

    if not os.path.exists(PROFILE_DIR):
        print(f"{C.RED}X No saved session. Run 'py submit.py --login' first.{C.RESET}")
        sys.exit(1)

    context = make_context(playwright, headless=True)
    page = stealth_page(context.new_page())

    # ── Step 1: Check we're still logged in ──
    print(f"{C.CYAN}-> Verifying session...{C.RESET}")
    page.goto(CODEFORCES_URL, timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    content = page.content()
    if f'handle = "{HANDLE}"' not in content:
        # Try navigating to enter page to check
        if "challenge" in content.lower() or len(content) < 2000:
            print(f"{C.RED}X Cloudflare blocked headless browser.{C.RESET}")
            print(f"  Run 'py submit.py --login' to refresh your session.")
        else:
            print(f"{C.RED}X Not logged in. Run 'py submit.py --login' first.{C.RESET}")
        context.close()
        sys.exit(1)

    print(f"  {C.GREEN}OK Logged in as {HANDLE}{C.RESET}")

    # ── Step 2: Navigate to submit page ──
    print(f"{C.CYAN}-> Opening submit page...{C.RESET}")
    submit_url = f"{CODEFORCES_URL}/contest/{contest_id}/submit/{problem_index}"
    page.goto(submit_url, timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    if "/enter" in page.url or "login" in page.url:
        print(f"{C.RED}X Session expired. Run 'py submit.py --login' again.{C.RESET}")
        context.close()
        sys.exit(1)

    print(f"  {C.GREEN}OK Submit page loaded{C.RESET}")

    # ── Step 3: Fill the form ──
    print(f"{C.CYAN}-> Filling submission form...{C.RESET}")
    try:
        # Select problem index (in case the page has a selector)
        prob_sel = page.locator('select[name="submittedProblemIndex"]')
        if prob_sel.count() > 0:
            prob_sel.select_option(problem_index)

        # Select language
        lang_sel = page.locator('select[name="programTypeId"]')
        if lang_sel.count() > 0:
            lang_sel.select_option(str(lang_id))
        else:
            print(f"{C.YELLOW}  ! Could not find language selector{C.RESET}")

        page.wait_for_timeout(500)

        # Enable text editor mode (if there's a toggle)
        toggle = page.locator("#toggleEditorCheckbox")
        if toggle.count() > 0:
            is_checked = toggle.is_checked()
            if not is_checked:
                toggle.click()
                page.wait_for_timeout(500)

        # Paste into source textarea
        textarea = page.locator("#sourceCodeTextarea")
        if textarea.count() > 0:
            textarea.fill(source_code)
        else:
            # Some CF pages use a CodeMirror/ACE editor — try clicking and typing
            editor = page.locator(".ace_editor, .CodeMirror")
            if editor.count() > 0:
                editor.first.click()
                page.keyboard.press("Control+a")
                page.keyboard.type(source_code)
            else:
                # Last resort: file upload
                file_input = page.locator('input[name="sourceFile"]')
                if file_input.count() > 0:
                    tmp = os.path.join(SCRIPT_DIR, ".tmp_submit" + os.path.splitext(filename)[1])
                    with open(tmp, "w", encoding="utf-8") as f:
                        f.write(source_code)
                    file_input.set_input_files(tmp)
                else:
                    print(f"{C.RED}X Cannot find code input on page.{C.RESET}")
                    context.close()
                    sys.exit(1)

    except Exception as e:
        print(f"{C.RED}X Error filling form: {e}{C.RESET}")
        context.close()
        sys.exit(1)

    print(f"  {C.GREEN}OK Form filled{C.RESET}")

    # ── Step 4: Submit ──
    print(f"{C.CYAN}-> Clicking Submit...{C.RESET}")
    try:
        btn = page.locator('input[type="submit"].submit, input[value="Submit"]')
        btn.first.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"{C.RED}X Submit click failed: {e}{C.RESET}")
        context.close()
        sys.exit(1)

    # Check for errors
    error_el = page.locator(".error, .verdict-rejected")
    if error_el.count() > 0:
        err = error_el.first.inner_text().strip()
        if err:
            print(f"{C.RED}X Submit error: {err}{C.RESET}")
            context.close()
            sys.exit(1)

    if "same code" in page.content():
        print(f"{C.YELLOW}! Already submitted this exact code before.{C.RESET}")
        context.close()
        sys.exit(1)

    print(f"  {C.GREEN}OK Submitted!{C.RESET}")
    context.close()

    # Cleanup temp file
    tmp = os.path.join(SCRIPT_DIR, ".tmp_submit" + os.path.splitext(filename)[1])
    if os.path.exists(tmp):
        os.remove(tmp)


# ─── VERDICT POLLING ─────────────────────────────────────────────────────────

def get_latest_sub_id():
    """Get the most recent submission ID before we submit (to detect the new one)"""
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
    """Poll until a new submission for this contest appears with a final verdict"""
    api_url = f"{CODEFORCES_URL}/api/user.status?handle={HANDLE}&from=1&count=5"

    print(f"\n{C.CYAN}Waiting for verdict...{C.RESET}", end="", flush=True)

    for _ in range(120):  # 4 min max
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

    print(f"\n{C.YELLOW}! Timed out. Check on the website.{C.RESET}")
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

    vc = C.GREEN if verdict == "OK" else C.RED

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
    from playwright.sync_api import sync_playwright

    if len(sys.argv) < 2:
        print(f"{C.BOLD}Codeforces Submit Tool{C.RESET}")
        print(f"  py submit.py --login      Log in (one-time)")
        print(f"  py submit.py <file>       Submit a solution")
        sys.exit(0)

    with sync_playwright() as pw:
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

        print(f"\n{C.BOLD}{'-' * 54}{C.RESET}")
        print(f"  {C.CYAN}Codeforces Submit{C.RESET}")
        print(f"    File:     {filename}")
        print(f"    Contest:  {contest_id}")
        print(f"    Problem:  {problem_index}")
        print(f"    Language: {LANG_NAMES.get(lang_id, '?')}")
        print(f"    Lines:    {len(source_code.splitlines())}")
        print(f"{C.BOLD}{'-' * 54}{C.RESET}\n")

        # Record current latest submission ID
        old_id = get_latest_sub_id()

        # Submit
        do_submit(pw, filename, contest_id, problem_index, source_code, lang_id)

        # Poll verdict
        result = poll_verdict(contest_id, old_id)
        if result:
            display_verdict(result)
            sys.exit(0 if result.get("verdict") == "OK" else 1)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
