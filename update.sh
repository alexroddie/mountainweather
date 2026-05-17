#!/bin/bash
set -ex

# Ensure the system knows where to find binaries
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin

# Change to your working directory
cd /var/services/homes/alex/scripts/mountainweather/

# SET YOUR HARD-CODED VERIFIED GIT PATH
GIT_EXEC="/volume1/@appstore/Git/bin/git"

# 1. Housekeeping
if [ -d "logs" ]; then
    find ./logs -name "error_*.txt" -type f -mtime +30 -delete
fi

# 2. Clear out previous error logs.
rm -f python_error.txt
rm -f git_error.txt
rm -f build_log.txt

# 3. Execute the Python Build.
if ! python3 build.py > build_log.txt 2>&1; then
    echo "MOUNTAIN DASHBOARD: PYTHON SCRIPT FAILURE"
    cat build_log.txt > python_error.txt
    exit 1
fi

# 4. Proceed with the Git push using the hard-coded path.
$GIT_EXEC add trmnl.html README.md Readme.html update.sh build.py > git_error.txt 2>&1
$GIT_EXEC commit --amend --allow-empty -m "Automated build from Synology: $(date +'%Y-%m-%d %H:%M')" >> git_error.txt 2>&1
$GIT_EXEC push origin main --force >> git_error.txt 2>&1