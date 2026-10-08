"""
greytHR attendance punch: logs in, then clicks Sign In or Sign Out.

Usage:
    python greythr_punch.py in                      # Sign In
    python greythr_punch.py out                     # Sign Out
    python greythr_punch.py in --headed --dry-run   # visible browser, log in + find button, don't click
    python greythr_punch.py out --force             # bypass weekday/time-window rules (manual use)

Rules (skipped unless --force):
    - Saturday / Sunday: never punches.
    - Sign In : only Mon-Fri between SIGNIN_WINDOW  (late sign-in is allowed).
    - Sign Out: only Mon-Fri between SIGNOUT_WINDOW (late sign-out allowed until 23:55).
    Catch-up runs from a missed day that land outside these windows are skipped.
"""
import sys
import datetime as dt
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------- CONFIG ----------------
BASE_URL = "https://bearingpoint-mv.greythr.com"   # change if your company's greytHR URL differs
USERNAME = ""   # fill these: your greytHR employee ID / login, e.g. "BPI123"
PASSWORD = ""   # fill these: your greytHR password (or leave "" and use: python -m keyring set greythr <employee id>)

SIGNIN_WINDOW = ("09:30", "23:55")   # Sign In allowed from scheduled time until end of day
SIGNOUT_WINDOW = ("18:00", "23:55")  # Sign Out allowed from scheduled time until 23:55
WORKDAYS = {0, 1, 2, 3, 4}           # Mon=0 ... Fri=4

LOGIN_FORM_TIMEOUT = 5_000     # ms to wait for login form to appear
LOGIN_DONE_TIMEOUT = 45_000    # ms to wait for login to complete
BUTTON_TIMEOUT = 45_000        # ms to wait for Sign In / Sign Out button
BROWSER_CHANNEL = "msedge"     # "msedge" (installed Edge), "chrome", or "" for Playwright Chromium
# ----------------------------------------

LOG_DIR = Path(__file__).with_name("greythr_logs")
ACTIONS = {"in": "Sign In", "out": "Sign Out"}
WINDOWS = {"in": SIGNIN_WINDOW, "out": SIGNOUT_WINDOW}


def log(msg: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG_DIR / "punch.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _hm(s: str) -> dt.time:
    h, m = s.split(":")
    return dt.time(int(h), int(m))


def allowed_now(mode: str, label: str) -> bool:
    now = dt.datetime.now()
    if now.weekday() not in WORKDAYS:
        log(f"SKIP: {now:%A} is not a workday, no '{label}'")
        return False
    start, end = (_hm(t) for t in WINDOWS[mode])
    if not (start <= now.time() <= end):
        log(f"SKIP: {now:%H:%M} outside '{label}' window {WINDOWS[mode][0]}-{WINDOWS[mode][1]}")
        return False
    return True


def get_password() -> str:
    if PASSWORD:
        return PASSWORD
    try:
        import keyring
        return keyring.get_password("greythr", USERNAME) or ""
    except Exception:
        return ""


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ACTIONS:
        print(__doc__)
        return 2
    mode = sys.argv[1]
    label = ACTIONS[mode]
    headed = "--headed" in sys.argv
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    if not force and not allowed_now(mode, label):
        return 0

    if not USERNAME:
        log("ERROR: USERNAME is empty. Fill in your employee ID at the top of greythr_punch.py")
        return 1

    password = get_password()
    if not password:
        log("ERROR: no password. Set PASSWORD in the script or run: python -m keyring set greythr <employee id>")
        return 1

    stamp = f"{dt.datetime.now():%Y%m%d_%H%M%S}_{mode}"
    LOG_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, channel=BROWSER_CHANNEL or None)
        page = browser.new_context().new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)

            if "microsoftonline" in page.url or "okta" in page.url:
                raise RuntimeError(f"Redirected to SSO ({page.url}); password login not possible")

            # ---- Login ----
            pwd_box = page.locator("input[type=password]").first
            try:
                pwd_box.wait_for(state="visible", timeout=LOGIN_FORM_TIMEOUT)
                on_login = True
            except PWTimeout:
                on_login = False

            if on_login:
                page.wait_for_timeout(1000)
                user_box = page.locator(
                    "input[name=username], #username, input[type=text], input:not([type])"
                ).first
                user_box.click()
                user_box.fill(USERNAME)
                pwd_box.click()
                pwd_box.fill(password)
                page.wait_for_timeout(500)
                page.locator(
                    "button[type=submit], button:has-text('Log in'), button:has-text('Login'), button:has-text('Sign in')"
                ).first.click()
                try:
                    pwd_box.wait_for(state="detached", timeout=LOGIN_DONE_TIMEOUT)
                except PWTimeout:
                    raise RuntimeError("Still on login page after submit (wrong password / captcha / selector)")
                page.wait_for_load_state("networkidle", timeout=60_000)
                page.wait_for_timeout(3000)  # let dashboard widgets render

            # ---- Attendance button ----
            btn = page.get_by_role("button", name=label, exact=True)
            try:
                btn.wait_for(state="visible", timeout=BUTTON_TIMEOUT)
            except PWTimeout:
                other = ACTIONS["out" if mode == "in" else "in"]
                if page.get_by_role("button", name=other, exact=True).count():
                    log(f"SKIP: '{label}' not shown; already in that state ('{other}' visible)")
                    return 0
                raise RuntimeError(f"'{label}' button not found")

            if dry_run:
                page.screenshot(path=str(LOG_DIR / f"{stamp}_DRYRUN.png"), full_page=True)
                log(f"DRY RUN: login OK, '{label}' button found, not clicked")
                if headed:
                    page.wait_for_timeout(10_000)
                return 0

            btn.click()

            # Some tenants show a confirm dialog with the same label
            page.wait_for_timeout(1500)
            confirm = page.get_by_role("button", name=label, exact=True)
            if confirm.count() > 0 and confirm.first.is_visible():
                confirm.first.click()

            page.wait_for_timeout(3000)
            page.screenshot(path=str(LOG_DIR / f"{stamp}.png"), full_page=True)
            log(f"OK: clicked '{label}'")
            return 0
        except Exception as e:
            try:
                page.screenshot(path=str(LOG_DIR / f"{stamp}_ERROR.png"), full_page=True)
            except Exception:
                pass
            log(f"ERROR: {e}")
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
