The runbot build of the branch checked out at /app is red. I pasted the relevant parts of the build logs in /home/odoo/runbot_log.txt: a warning repeated at every module load, an installation error that kills the all-modules build, and a failing test in the l10n build.

Fixes already exist in master for part of it, I exported them as patches in /home/odoo/patches/ (one of them is unrelated to the log, it's a crash fix I also want on this branch). Backport what is needed, and handle the rest, so that the build goes green. Commit on the current branch, mentioning the original revision when you backport one. Do not push.

PostgreSQL runs locally and your user can create databases.
