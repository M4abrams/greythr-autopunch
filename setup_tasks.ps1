# Creates two Windows scheduled tasks: greytHR Sign In (09:30) and Sign Out (18:00), Mon-Fri.
# Run from the folder containing greythr_punch.py:  powershell -ExecutionPolicy Bypass -File .\setup_tasks.ps1
param(
    [string]$SignInTime  = "09:30",
    [string]$SignOutTime = "18:00"
)

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyw = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw.exe"
if (!(Test-Path $pyw)) {
    $pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
}
if (!$pyw) { Write-Error "pythonw.exe not found. Install Python 3.12 first."; exit 1 }

$days = "Monday","Tuesday","Wednesday","Thursday","Friday"
$set  = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

foreach ($t in @(@{n="greytHR Sign In"; a="in"; at=$SignInTime}, @{n="greytHR Sign Out"; a="out"; at=$SignOutTime})) {
    $act  = New-ScheduledTaskAction -Execute $pyw -Argument "`"$dir\greythr_punch.py`" $($t.a)" -WorkingDirectory $dir
    $trig = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $t.at
    Register-ScheduledTask -TaskName $t.n -Action $act -Trigger $trig -Settings $set -Force | Out-Null
}
Get-ScheduledTask -TaskName "greytHR*" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
