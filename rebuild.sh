#!/bin/bash
# This runs on PythonAnywhere servers (deploy.sh calls it): fetches new
# code, installs needed packages, and reloads the web app.
# Stops at the first step that fails, so a broken pull or install never
# reloads the web app.
#
# Needs in the environment: PA_USER, VENV, PA_DOMAIN (deploy.sh sets
# them), and API_TOKEN for pa_reload_webapp.py (set it in ~/.bashrc:
# export API_TOKEN=<your PythonAnywhere API token>).
set -euo pipefail

: "${PA_USER:?Set PA_USER to the PythonAnywhere account name.}"
: "${VENV:?Set VENV to the virtualenv name in ~/.virtualenvs.}"
: "${PA_DOMAIN:?Set PA_DOMAIN to the web app domain.}"
# The ssh session from deploy.sh may not read ~/.bashrc:
if [ -z "${API_TOKEN:-}" ] && [ -f ~/.bashrc ]; then
    set +u
    # shellcheck disable=SC1090
    source ~/.bashrc
    set -u
fi
: "${API_TOKEN:?Set API_TOKEN (export it in ~/.bashrc) to reload the web app.}"

cd "$(dirname "$0")"
touch rebuild
echo "Rebuilding $PA_DOMAIN"

echo "Pulling code from master"
git pull origin master

echo "Activate the virtual env $VENV for user $PA_USER"
set +u
source "/home/$PA_USER/.virtualenvs/$VENV/bin/activate"
set -u

echo "Install packages"
pip install --upgrade -r requirements.txt

echo "Reloading the web app"
pa_reload_webapp.py "$PA_DOMAIN"

touch reboot
echo "Finished rebuild."
