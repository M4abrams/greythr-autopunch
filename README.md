# greytHR Auto Punch

Automatically clicks **Sign In** and **Sign Out** on greytHR, **Monday to Friday only**, using Windows Task Scheduler.

| What it does | Details |
|---|---|
| Logs in | Uses your employee ID and password |
| Signs in | Every weekday at **09:30** (default) |
| Signs out | Every weekday at **18:00** (default) |
| Weekends | Never punches on Saturday or Sunday |
| Late runs | If your PC was asleep, a late Sign In (until 23:55) or late Sign Out (18:00 to 23:55) still happens. Catch-up runs outside these windows are skipped. |
| Already punched | Skips the click if you're already signed in/out |
| Logging | Every run is written to `greythr_logs\punch.log`, with a screenshot |

> **Requirements:** Windows 10/11, greytHR login with **username + password**.
> It does **not** work if your company signs in to greytHR through Microsoft, Okta or another SSO page.

---

## Contents
1. [Download the project](#1-download-the-project)
2. [Install Python](#2-install-python)
3. [Install the Python packages](#3-install-the-python-packages-playwright-keyring)
4. [Check the browser (Edge)](#4-check-the-browser-edge)
5. [Enter your details](#5-enter-your-details)
6. [Test it without punching](#6-test-it-without-punching)
7. [Create the scheduled tasks](#7-create-the-scheduled-tasks)
8. [Allow the laptop to wake up](#8-allow-the-laptop-to-wake-up)
9. [Verify the scheduler works](#9-verify-the-scheduler-works)
10. [Daily use: viewing the log](#10-daily-use-viewing-the-log)
11. [Changing times, updating, uninstalling](#11-changing-times-updating-uninstalling)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Download the project

1. On this GitHub page, click the green **`<> Code`** button → **Download ZIP**.
2. Open your **Downloads** folder, right-click the ZIP → **Extract All…**
3. Move the extracted folder to **`C:\GreytHR`**, so that this file exists:
   ```
   C:\GreytHR\greythr_punch.py
   ```

> ⚠️ Use a local drive (`C:\`). Don't use OneDrive, Desktop (if synced to OneDrive) or a mapped network drive. Scheduled tasks often can't see those, and your password would sync to the cloud.

All commands below are run in **PowerShell**:
press **Start**, type `PowerShell`, and open **Windows PowerShell** (no admin needed).

---

## 2. Install Python

### 2a. Check whether Python is already installed
```powershell
Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
```
- `True` → Python 3.12 is installed. Skip to **2c**.
- `False` → continue with **2b**.

> Don't rely on typing `python --version`. On many PCs it opens a Microsoft Store placeholder
> ("Python was not found; run without arguments to install from the Microsoft Store…") even when Python is installed.

### 2b. Install Python 3.12
**Option 1, winget (recommended):**
```powershell
winget install -e --id Python.Python.3.12 --scope user
```
If it says *"Found an existing package already installed"*, Python is already there. Continue.

**Option 2, installer (if winget is blocked by your company):**
1. Go to https://www.python.org/downloads/windows/ and download **Windows installer (64-bit)** for Python 3.12.
2. Run it. On the first screen, **tick "Add python.exe to PATH"**.
3. Click **Customize installation** → Next → make sure **"Install Python 3.12 for all users" is unticked** (no admin needed) → Install.

**Close PowerShell and open a new window** after installing.

### 2c. Create a shortcut variable for Python
Every time you open a **new** PowerShell window, run this line first:
```powershell
$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
```
Then check it works:
```powershell
& $python --version
```
Expected: `Python 3.12.x`

> Why `& $python` instead of `python`? It calls Python by its full path, which avoids PATH problems and the Microsoft Store placeholder completely.
> If you see `The expression after '&' in a pipeline element produced an object that was not valid`, you forgot to run the `$python = ...` line in this window.

<details>
<summary>Optional: set $python automatically in every new window</summary>

```powershell
if (!(Test-Path $PROFILE)) { New-Item $PROFILE -Force | Out-Null }
Add-Content $PROFILE '$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"'
```
If your company blocks PowerShell profiles ("running scripts is disabled"), just keep running the `$python = ...` line manually.
</details>

<details>
<summary>Optional: make plain "python" work</summary>

Settings → Apps → Advanced app settings → **App execution aliases** → turn **off** `python.exe` and `python3.exe`.
</details>

---

## 3. Install the Python packages (playwright, keyring)

```powershell
cd C:\GreytHR
& $python -m pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| **playwright** | Controls the browser: opens greytHR, types your login, clicks the button |
| **keyring** | Optional: lets you store the password in Windows Credential Manager instead of the file |

Expected ending: `Successfully installed ... playwright-x.x.x ... keyring-x.x.x`

> **Do you need `playwright install`?** No, not by default. The script uses the **Microsoft Edge** that's already on Windows.
> (Running `playwright install chromium` downloads a separate browser and is often blocked on office networks with a timeout error. You can skip it.)

---

## 4. Check the browser (Edge)

```powershell
Test-Path "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
```
- `True` → nothing to do.
- `False` → open `greythr_punch.py` and change the browser line to one of these:
  ```python
  BROWSER_CHANNEL = "chrome"   # if Google Chrome is installed
  BROWSER_CHANNEL = ""         # use Playwright's own browser
  ```
  If you chose `""`, also run:
  ```powershell
  & $python -m playwright install chromium
  ```

---

## 5. Enter your details

Open the file in Notepad:
```powershell
notepad C:\GreytHR\greythr_punch.py
```
At the top, fill in the CONFIG section:
```python
BASE_URL = "https://bearingpoint-mv.greythr.com"   # change if your company's greytHR URL differs
USERNAME = ""   # fill these: your greytHR employee ID / login, e.g. "BPI123"
PASSWORD = ""   # fill these: your greytHR password
```
Example:
```python
USERNAME = "BPI123"
PASSWORD = "MyP@ssw0rd"
```
Save (**Ctrl+S**) and close Notepad.

| Setting | What to put |
|---|---|
| `BASE_URL` | The address you open greytHR with, e.g. `https://yourcompany.greythr.com`, without anything after `.com` |
| `USERNAME` | Your employee ID exactly as you type it on the greytHR login page |
| `PASSWORD` | Your greytHR password, inside the quotes |

<details>
<summary>Don't want the password in the file? Use Windows Credential Manager instead</summary>

Leave `PASSWORD = ""` and run (replace BPI123 with your ID):
```powershell
& $python -m keyring set greythr BPI123
```
Type your password at the prompt (nothing shows on screen while typing) and press Enter.
Re-run this whenever your greytHR password changes.
</details>

> 🔒 Never upload your filled-in `greythr_punch.py` anywhere. It contains your password.

---

## 6. Test it without punching

The `--dry-run` option logs in and finds the button **but does not click it**. `--headed` shows the browser so you can watch.

```powershell
cd C:\GreytHR
& $python greythr_punch.py in --headed --dry-run
```

An Edge window opens, fills in your login, opens the dashboard and stays for 10 seconds.

| Output | Meaning |
|---|---|
| `DRY RUN: login OK, 'Sign In' button found, not clicked` | ✅ Everything works |
| `SKIP: 'Sign In' not shown; already in that state ('Sign Out' visible)` | ✅ Works; you're already signed in today |
| `SKIP: Saturday is not a workday` / `SKIP: 08:15 outside 'Sign In' window` | Weekend or before 09:30. Add `--force` to test anyway: `& $python greythr_punch.py in --headed --dry-run --force` |
| `ERROR: USERNAME is empty` / `ERROR: no password` | Step 5 not done or not saved |
| `ERROR: Still on login page after submit` | Wrong ID/password, or a captcha appeared. Watch the Edge window to see which |
| `ERROR: Redirected to SSO` | Your company uses Microsoft/Okta login. Not supported |

The first run can take up to a minute. If the PowerShell cursor is blinking with no prompt, it's still working.

---

## 7. Create the scheduled tasks

This creates two Windows scheduled tasks, **greytHR Sign In** and **greytHR Sign Out**, Monday to Friday:
```powershell
cd C:\GreytHR
powershell -ExecutionPolicy Bypass -File .\setup_tasks.ps1
```
Expected output:
```
TaskName         NextRunTime
--------         -----------
greytHR Sign In  <next weekday> 09:30:00
greytHR Sign Out <next weekday> 18:00:00
```

**Different times:**
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_tasks.ps1 -SignInTime 09:00 -SignOutTime 18:30
```
If you change the times, also edit these lines in `greythr_punch.py` so the earliest allowed time matches:
```python
SIGNIN_WINDOW = ("09:00", "23:55")
SIGNOUT_WINDOW = ("18:30", "23:55")
```

<details>
<summary>What the tasks are configured to do</summary>

| Setting | Why |
|---|---|
| Runs `pythonw.exe` (no console window) | Runs silently in the background |
| Wake the computer to run | Punches even if the laptop is asleep (needs step 8) |
| Run as soon as possible after a missed start | If the PC was off, it punches when you turn it on (the script's weekday/time rules still apply) |
| Run on battery | Doesn't skip when unplugged |
| Retry 3 times, every 5 minutes | Handles temporary network/greytHR errors |
| Only when you're logged in to Windows | A locked screen is fine; signed out of Windows is not |

You can see them in **Task Scheduler** (Start → type `Task Scheduler`) under *Task Scheduler Library*.
</details>

---

## 8. Allow the laptop to wake up

Without this, a sleeping laptop punches only when you wake it.

1. Start → type **Edit power plan** → open it.
2. Click **Change advanced power settings**.
3. Expand **Sleep → Allow wake timers** → set to **Enable** (both *On battery* and *Plugged in*).
4. Click **OK**.

> A laptop that's **shut down** (not asleep) can't be woken. It punches after you turn it on and log in, if still within the allowed time window.

---

## 9. Verify the scheduler works

Run the Sign Out task now. If it's before 18:00 it will safely **skip** and only write a log line, which proves the scheduler can run the script:
```powershell
Start-ScheduledTask -TaskName "greytHR Sign Out"
Start-Sleep 20
Get-Content C:\GreytHR\greythr_logs\punch.log -Tail 3
Get-ScheduledTaskInfo -TaskName "greytHR Sign Out" | Select LastRunTime, LastTaskResult
```
- A new `SKIP: ... outside 'Sign Out' window` line and `LastTaskResult : 0` → ✅ done.
- No new line / non-zero result → see [Troubleshooting](#12-troubleshooting).

---

## 10. Daily use: viewing the log

```powershell
Get-Content C:\GreytHR\greythr_logs\punch.log -Tail 15
```
Or open it in Notepad: `notepad C:\GreytHR\greythr_logs\punch.log`
Screenshots of each run: `explorer C:\GreytHR\greythr_logs`

Example of a healthy week:
```
2026-10-06 09:30:20 OK: clicked 'Sign In'
2026-10-06 18:00:19 OK: clicked 'Sign Out'
2026-10-07 09:30:26 OK: clicked 'Sign In'
2026-10-07 18:00:22 OK: clicked 'Sign Out'
```

| Log line | Meaning |
|---|---|
| `OK: clicked 'Sign In'` / `'Sign Out'` | Punched |
| `SKIP: ... already in that state` | Already signed in/out; nothing clicked |
| `SKIP: Saturday is not a workday` | Weekend; nothing clicked |
| `SKIP: hh:mm outside ... window` | Stale/early catch-up run; nothing clicked |
| `ERROR: ...` | Failed. Check the matching `*_ERROR.png` screenshot |
| A time much later than scheduled (e.g. `10:05 OK: clicked 'Sign In'`) | PC was asleep/off; punched late. Regularize in greytHR if needed |

**Manual commands** (set `$python` first, run from `C:\GreytHR`):

| Command | Effect |
|---|---|
| `& $python greythr_punch.py in` | Sign In now (weekday/time rules apply) |
| `& $python greythr_punch.py out` | Sign Out now (weekday/time rules apply) |
| add `--dry-run` | Log in and find the button, don't click |
| add `--headed` | Show the browser window |
| add `--force` | Ignore weekday/time rules |

---

## 11. Changing times, updating, uninstalling

**Change punch times:** re-run step 7 with new `-SignInTime` / `-SignOutTime` and update the windows in the script.

**Password changed:** update `PASSWORD` in `greythr_punch.py` (or re-run the `keyring set` command).

**Pause for a holiday/leave:**
```powershell
Disable-ScheduledTask -TaskName "greytHR Sign In"
Disable-ScheduledTask -TaskName "greytHR Sign Out"
# resume:
Enable-ScheduledTask -TaskName "greytHR Sign In"
Enable-ScheduledTask -TaskName "greytHR Sign Out"
```

**Update to a newer version of this project:** download the new ZIP, replace `greythr_punch.py`, and fill in USERNAME/PASSWORD again.

**Uninstall:**
```powershell
Unregister-ScheduledTask -TaskName "greytHR Sign In" -Confirm:$false
Unregister-ScheduledTask -TaskName "greytHR Sign Out" -Confirm:$false
Remove-Item C:\GreytHR -Recurse
```

---

## 12. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `py` / `python` "is not recognized" | Python not on PATH | Use `$python` (step 2c) |
| `Python was not found; run without arguments to install from the Microsoft Store` | Windows Store placeholder | Use `$python` (step 2c), or turn off the App execution aliases |
| `The expression after '&' ... was not valid` | New PowerShell window | Run `$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"` again |
| `winget` "is not recognized" or blocked | Company policy | Use the python.org installer (step 2b, option 2) |
| `pip install` fails with SSL / proxy / timeout | Office network | Try on home Wi-Fi or a mobile hotspot, or ask IT |
| `Executable doesn't exist at ...chrome-win64\chrome.exe` | Script set to Playwright Chromium, not installed | Set `BROWSER_CHANNEL = "msedge"` |
| `playwright install` → `timed out after 30000ms` | Office network blocks the download | Not needed. Keep `BROWSER_CHANNEL = "msedge"` |
| `Chromium distribution 'msedge' is not found` | Edge missing | Step 4 |
| `ERROR: Still on login page after submit` | Wrong ID/password, captcha, or slow site | Run with `--headed` and watch; check the `*_ERROR.png` |
| `ERROR: 'Sign In' button not found` | Page didn't load, or greytHR changed its layout | Check the `*_ERROR.png`; try `--headed` |
| `ERROR: Redirected to SSO` | Company uses Microsoft/Okta login | Not supported |
| Nothing in the log at 09:30/18:00 | PC off/asleep, or wake timers disabled | Step 8; check `Get-ScheduledTaskInfo -TaskName "greytHR Sign In"` |
| `LastTaskResult` is not `0` | Task couldn't start (often the folder is on a network/OneDrive drive) | Move the folder to `C:\GreytHR` and re-run step 7 |
| Punched on a weekend | Old version of the script | Download the latest version |
| `running scripts is disabled on this system` | PowerShell policy | Always use `powershell -ExecutionPolicy Bypass -File .\setup_tasks.ps1` |

Still stuck? Open an **Issue** on this repo with the log line and the `*_ERROR.png` screenshot (**cover your employee ID in the screenshot**).

---

## Disclaimer
Check your company's attendance policy before using this. Use at your own risk.
