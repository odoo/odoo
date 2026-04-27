from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResUser(models.Model):
    _inherit = "res.users"

    # bis number is for foreigners in Belgium
    insz_or_bis_number = fields.Char(
        "INSZ or BIS number", help="Social security identification number"
    )
    session_clocked_ids = fields.Many2many(
        "pos.session",
        "users_session_clocking_info",
        string="Session Clocked In",
        help="This is a technical field used for tracking the status of the session for each users.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        config_id = self.env["pos.config"].browse(config_id)
        if config_id.iface_fiscal_data_module:
            result += ['insz_or_bis_number']
        return result

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["insz_or_bis_number"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["insz_or_bis_number"]

    @api.constrains("insz_or_bis_number")
    def _check_insz_or_bis_number(self):
        for rec in self:
            if rec.insz_or_bis_number and not self.is_valid_insz_or_bis_number(rec.insz_or_bis_number):
                raise ValidationError(_("The INSZ or BIS number is not valid."))

    def is_valid_insz_or_bis_number(self, number):
        if not number:
            return False
        if len(number) != 11 or not number.isdigit():
            return False

        partial_number = number[:-2]
        modulo = int(partial_number) % 97

        if modulo == 97 - int(number[-2:]):
            return True

        # Allow employee and user born after 2000.
        partial_number = '2' + partial_number
        modulo = int(partial_number) % 97

        return modulo == 97 - int(number[-2:])
