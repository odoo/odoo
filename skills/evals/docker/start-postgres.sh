#!/bin/sh
# Entrypoint: start the odoo user's PostgreSQL cluster, then run the container's
# command (Harbor's keep-alive). Odoo reaches it on the default socket as odoo.
pg_ctl -D "$PGDATA" -l "$PGDATA/server.log" -w start > /dev/null
exec "$@"
