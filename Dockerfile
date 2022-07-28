FROM odoo:15
MAINTAINER Cubean <cubean@warp-driven.com>

COPY ./odoo /usr/lib/python3/dist-packages/

# Set default user when running the container
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]