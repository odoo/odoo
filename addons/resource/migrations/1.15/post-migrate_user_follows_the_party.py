import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT id, user_id FROM resource_resource WHERE resource_type = 'user'")
    before = dict(cr.fetchall())
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    resources = env["resource.resource"].browse(list(before))
    env.add_to_compute(resources._fields["user_id"], resources)
    env.flush_all()
    cr.execute("SELECT id, user_id FROM resource_resource WHERE resource_type = 'user'")
    changed = {
        resource_id: (before[resource_id], user_id)
        for resource_id, user_id in cr.fetchall()
        if before.get(resource_id) != user_id
    }
    _logger.info(
        "%s human resources took their party's user (resource: before -> after): %s",
        len(changed),
        changed,
    )
