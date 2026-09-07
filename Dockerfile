FROM odoo:19.0

USER root
RUN mkdir -p /opt/odoo-src /mnt/extra-addons \
    && chown -R odoo:odoo /opt/odoo-src /mnt/extra-addons
USER odoo
