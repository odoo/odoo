# Built on the shared eval image (skills/evals/docker), which must exist locally:
#     docker build -t odoo-evals:20.0 docker
FROM odoo-evals:20.0

# task: a checkout at a 20.0 commit, on the developer's feature branch.
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 50 origin c6f3b034f29220afa236737ab79d1228bdc9f3c0 \
    && git checkout -q -b 20.0-property-rental-jdoe FETCH_HEAD \
    && git remote remove origin

# task: the new module under review, committed on the branch. It is synthetic:
# every pattern of the odoo-security skill is planted in it, next to a few
# correct constructs that should not be reported.
COPY --chown=odoo property_rental /app/addons/property_rental
RUN git add addons/property_rental \
    && git commit -q -m "[ADD] property_rental: rent properties to portal tenants" \
        -m "Add a module to manage rental properties and their leases. Tenants follow their leases from the portal: they see the rent and where to pay it, update their notes, sign and cancel." \
        -m "task-4815162"
