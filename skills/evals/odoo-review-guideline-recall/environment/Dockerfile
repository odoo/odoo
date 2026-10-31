# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
# The image's Python environment is 20.0's; master's requirements.txt is the
# same at the base commit.
FROM odoo-evals:20.0

# task: a checkout at a master commit (20.1 alpha), on the developer's branch.
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 50 origin c8d7430e3e15acc9224c53fe6c512414107897c3 \
    && git checkout -q -b master-equipment-booking-jdoe FETCH_HEAD \
    && git remote remove origin

# task: the PR under review, committed on the branch. A new module,
# equipment_booking, with violations of the odoo-guidelines, odoo-security
# and odoo-review rules seeded one per spot, and a change to maintenance that
# breaks modules the diff does not show. The answer key is tests/*/judge.toml.
COPY --chown=odoo change.patch /tmp/change.patch
COPY --chown=odoo commit_message.txt /tmp/commit_message.txt
RUN git apply /tmp/change.patch && rm /tmp/change.patch \
    && git add -A \
    && git commit -q -F /tmp/commit_message.txt && rm /tmp/commit_message.txt
