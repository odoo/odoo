# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
# The image's Python environment is 20.0's; master's requirements.txt is the
# same at the base commit.
FROM odoo-evals:20.0

# task: a depth-1 checkout of master (20.1 alpha) on a dev branch, without
# network printing: the printer module is removed, and remove.patch takes out
# what stock_delivery built on it (the shipping label reports, the automatic
# printing options of operation types, the printer menus, access row, demo
# and tour), its translation entries, and the module's entries in
# .weblate.json and the JS tooling config. The removal is folded into the
# single commit, with its original author, committer and dates, so the history
# does not show it. The remote is removed so a fetch cannot bring the code
# back.
COPY --chown=odoo remove.patch /tmp/remove.patch
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 1 origin c8d7430e3e15acc9224c53fe6c512414107897c3 \
    && git checkout -q -b master-network-printing-jdoe FETCH_HEAD \
    && git remote remove origin \
    && rm -rf addons/printer \
    && git apply /tmp/remove.patch \
    && rm /tmp/remove.patch \
    && git add -A \
    && GIT_COMMITTER_NAME="$(git log -1 --format=%cn)" \
       GIT_COMMITTER_EMAIL="$(git log -1 --format=%ce)" \
       GIT_COMMITTER_DATE="$(git log -1 --format=%cd --date=raw)" \
       git commit -q --amend --no-edit --no-verify

# task: the product team's spec, outside the checkout.
COPY --chown=odoo spec.md /home/odoo/spec.md
