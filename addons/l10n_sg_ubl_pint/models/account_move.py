import uuid

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_sg_get_uuid(self):
        """ SG Pint requires us to generate a uuid, to avoid storing a new field on the move,
        we derive it from the dbuuid and the move id. """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        guid = uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(self.id))
        return str(guid)
