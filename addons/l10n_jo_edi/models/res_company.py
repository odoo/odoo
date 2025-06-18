from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jo_edi_sequence_income_source = fields.Char(string="Sequence of Income Source")
    l10n_jo_edi_secret_key = fields.Char(string="Jordan EINV Secret Key", groups="base.group_system")
    l10n_jo_edi_client_identifier = fields.Char(string="Jordan EINV Client ID", groups="base.group_system")
    l10n_jo_edi_taxpayer_type = fields.Selection(string="Taxpayer type", selection=[
        ('income', "Unregistered in the sales tax"),
        ('sales', "Registered in the sales tax"),
        ('special', "Registered in the special sales tax"),
    ])

    def _get_jo_icv_param_name(self):
        return f'l10n_jo_edi.icv_{self.id}'

    def _get_next_jo_icv(self):
        param_name = self._get_jo_icv_param_name()
        return self.env['ir.config_parameter'].sudo().get_param(param_name, default='1')

    def _increment_jo_icv(self, increment=1):
        previous_icv = int(self._get_next_jo_icv())
        param_name = self._get_jo_icv_param_name()
        self.env['ir.config_parameter'].sudo().set_param(param_name, previous_icv + increment)
