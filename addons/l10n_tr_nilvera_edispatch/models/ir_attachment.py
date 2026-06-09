from odoo import api, models
from odoo.fields import Domain


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.depends('name', 'res_field', 'description')
    def _compute_display_name(self):
        super()._compute_display_name()
        for attachment in self.filtered(lambda att: att.res_field == 'l10n_tr_nilvera_edispatch_xml_file' and att.description):
            attachment.display_name = f"{attachment.description} - {attachment.display_name}"

    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if value and operator.endswith('like') and operator not in Domain.NEGATIVE_OPERATORS:
            domain |= Domain('res_field', '=', 'l10n_tr_nilvera_edispatch_xml_file') & Domain('description', operator, value)
        return domain
