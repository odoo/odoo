# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_mimetype_exempt_groups(self):
        return super()._get_mimetype_exempt_groups() + ['mass_mailing.group_mass_mailing_user']
