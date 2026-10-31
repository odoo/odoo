# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
FROM odoo-evals:20.0

# task: a depth-1 checkout of 20.0 on a dev branch, with the merged fix for the
# missing tracking separators reverted (the stable fix 87e57ed44969 and its
# master cleanup 8a2f76a796d6). The revert is folded into the single commit,
# with its original author, committer and dates, so the history does not show
# it. The remote is removed so a fetch cannot bring the fix back.
COPY --chown=odoo revert.patch /tmp/revert.patch
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 1 origin df9daf5ea0b5d8f40389757cd8cdc78c81cf17d4 \
    && git checkout -q -b 20.0-mail-tracking-arrows-jdoe FETCH_HEAD \
    && git remote remove origin \
    && git apply /tmp/revert.patch \
    && rm /tmp/revert.patch \
    && git add -A \
    && GIT_COMMITTER_NAME="$(git log -1 --format=%cn)" \
       GIT_COMMITTER_EMAIL="$(git log -1 --format=%ce)" \
       GIT_COMMITTER_DATE="$(git log -1 --format=%cd --date=raw)" \
       git commit -q --amend --no-edit --no-verify
