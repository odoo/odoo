from odoo.tools import consteq, escape_psql

from . import cdar
from . import drom_com_territories


def _get_matching_auth_record(model, object_uuid):
    records = model.search([
        ('pdp_authentication_uuid', '=like', f'{escape_psql(object_uuid)[:3]}%'),
    ], order='id DESC')
    return records.filtered(lambda record: consteq(record.pdp_authentication_uuid, object_uuid))[:1]
