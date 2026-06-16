FROM odoo:19

USER root

COPY --chmod=755 docker-entrypoint.sh /entrypoint.sh

# Bake custom addons into the image (for production).
# In dev, docker-compose volume-mounts override this.
COPY --chown=odoo:odoo custom_addons/ /mnt/extra-addons/

USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]
