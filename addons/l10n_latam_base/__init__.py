# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from odoo import api, SUPERUSER_ID


def _set_default_identification_type(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.partner'].search([]).write({'l10n_latam_identification_type_id': env.ref('l10n_latam_base.it_vat').id})
