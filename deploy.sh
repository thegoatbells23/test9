#!/bin/bash
# Deploy the latest master to our PythonAnywhere web app:
# SSH in to PythonAnywhere and run rebuild.sh there.
#
# Needs in the environment:
#   PA_USER    the PythonAnywhere account name
#   PA_PWD     that account's password (never printed)
# Optional:
#   PROJ_DIR   the repo's directory in the PA home dir  (default: HKH)
#   VENV       the virtualenv in ~/.virtualenvs on PA   (default: geodata2026)
#   PA_DOMAIN  the web app's domain             (default: $PA_USER.pythonanywhere.com)
set -euo pipefail

: "${PA_USER:?Set PA_USER to the PythonAnywhere account name.}"
: "${PA_PWD:?Set PA_PWD to the PythonAnywhere password.}"
PROJ_DIR=${PROJ_DIR:-HKH}
VENV=${VENV:-geodata2026}
PA_DOMAIN=${PA_DOMAIN:-$PA_USER.pythonanywhere.com}

echo "PA user = $PA_USER"
echo "PA domain = $PA_DOMAIN"
echo "Project dir = ~/$PROJ_DIR"
echo "Virtual env = $VENV"

echo "SSHing to PythonAnywhere."
# sshpass -e reads the password from SSHPASS, so it is not on the
# command line, where other users could see it with ps:
SSHPASS=$PA_PWD sshpass -e \
    ssh -o "StrictHostKeyChecking no" "$PA_USER@ssh.pythonanywhere.com" << EOF
cd ~/$PROJ_DIR && PA_USER=$PA_USER VENV=$VENV PA_DOMAIN=$PA_DOMAIN ./rebuild.sh
EOF
