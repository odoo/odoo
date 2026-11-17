# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
FROM odoo-evals:20.0

# task: the runbot image of the scenario lacks google-auth, which is why its
# all-modules build cannot install cloud_storage_google. The shared image has
# the library: remove it, so the checkout reproduces the log.
USER root
RUN apt-get remove -y python3-google-auth > /dev/null && rm -rf /var/lib/apt/lists/*
USER odoo

# task: the runbot log and the patches exported from master, outside the checkout
COPY --chown=odoo runbot_log.txt /home/odoo/runbot_log.txt
COPY --chown=odoo patches /home/odoo/patches

# task: a depth-1 checkout of 20.0 on a dev branch, with the old
# l10n_it_country_code field of l10n_it_stock_ddt planted back (it duplicates
# stock_account's country_code) and a test of the DDT sequence renaming that
# hits the real KeyError in write() and calls the method as master's patch
# would define it. The plant is folded into the single commit, with its
# original author, committer and dates, so the history does not show it. The
# remote is removed so a fetch cannot bring the branch's state back.
COPY --chown=odoo plant.patch /tmp/plant.patch
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 1 origin cd368a6d2fc65be3361f631d992fead30235cd21 \
    && git checkout -q -b 20.0-fix-runbot-red-jdoe FETCH_HEAD \
    && git remote remove origin \
    && git apply /tmp/plant.patch \
    && rm /tmp/plant.patch \
    && git add -A \
    && GIT_COMMITTER_NAME="$(git log -1 --format=%cn)" \
       GIT_COMMITTER_EMAIL="$(git log -1 --format=%ce)" \
       GIT_COMMITTER_DATE="$(git log -1 --format=%cd --date=raw)" \
       git commit -q --amend --no-edit --no-verify
