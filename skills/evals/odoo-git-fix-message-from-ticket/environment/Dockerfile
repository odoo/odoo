# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
FROM odoo-evals:20.0

# task: a checkout at the base commit, on a dev branch.
# Only the base commit and some history are fetched, so the merged fix and its
# message are not in the repository. The remote is removed so a fetch cannot
# bring them in.
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 50 origin c6f3b034f29220afa236737ab79d1228bdc9f3c0 \
    && git checkout -q -b 20.0-snailmail-cover-jdoe FETCH_HEAD \
    && git remote remove origin

# task: the fix, applied but not committed
COPY --chown=odoo change.patch /tmp/change.patch
RUN git apply /tmp/change.patch && rm /tmp/change.patch
