# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, registry, SUPERUSER_ID

def migrate(cr, version):
    # with registry(cr.dbname).cursor() as cr:
    #     env = api.Environment(cr, SUPERUSER_ID, {})
    env = api.Environment(cr, SUPERUSER_ID, {})
    formio_builder = env['formio.builder']

    for builder in formio_builder.search([]):
        builder.write({'uuid': formio_builder._default_uuid()})
