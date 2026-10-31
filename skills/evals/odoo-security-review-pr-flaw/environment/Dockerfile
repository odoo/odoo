# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
FROM odoo-evals:20.0

# task: a checkout at a 20.0 commit, on the developer's feature branch.
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 50 origin c6f3b034f29220afa236737ab79d1228bdc9f3c0 \
    && git checkout -q -b 20.0-payment-colleague-card-jdoe FETCH_HEAD \
    && git remote remove origin

# task: the PR under review, committed on the branch. An [IMP] that widens
# the token ownership check of /payment/transaction to same-company
# partners; any two partners without a company satisfy the comparison,
# which brings back CVE-2021-23178 (fixed by odoo/odoo 9a063023f9f7).
COPY --chown=odoo change.patch /tmp/change.patch
RUN git apply /tmp/change.patch && rm /tmp/change.patch \
    && git commit -q -a -m "[IMP] payment: pay with a card saved by a colleague" \
        -m "Customers with several contacts in the same company should be able to pay with a card one of them saved, instead of saving the same card again for each contact. Allow the payment when the paying partner and the token partner belong to the same company, keeping the check for every other case."