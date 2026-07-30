FROM odoo:19

USER root

# Align the container's odoo user with the host odoo user (UID 1000)
# so volume-mounted data dirs (/home/odoo/.local/share/Odoo) are
# writable without manual chown on the host.
RUN usermod -u 1000 odoo \
 && groupmod -g 1000 odoo \
 && chown -R 1000:1000 /var/lib/odoo /etc/odoo /mnt/extra-addons 2>/dev/null || true

COPY --chmod=755 docker-entrypoint.sh /entrypoint.sh

# Bake custom addons into the image (for production).
# In dev, docker-compose volume-mounts override this.
COPY --chown=odoo:odoo custom_addons/ /mnt/extra-addons/

USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]
