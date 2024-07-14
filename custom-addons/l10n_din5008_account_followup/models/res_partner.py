from odoo import models, fields, _
from odoo.tools import format_date

# Used for printing a follow-up letter

class Partner(models.Model):
    _inherit = 'res.partner'

    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')
    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')

    def _compute_l10n_din5008_template_data(self):
        for record in self:
            record.l10n_din5008_template_data = data = []
            data.append((_("Date:"), format_date(self.env, fields.Date.today())))
            addr = self.env['res.partner'].browse(record.address_get(['invoice'])['invoice']) or record
            if addr.ref:
                data.append((_("Customer ref:"), addr.ref))

    def _compute_l10n_din5008_document_title(self):
        for record in self:
            record.l10n_din5008_document_title = _('Payment Reminder')
