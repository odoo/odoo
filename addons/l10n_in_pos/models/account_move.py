# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_pos_session_ids = fields.One2many("pos.session", "move_id", "POS Sessions")

    @api.depends('l10n_in_pos_session_ids')
    def _compute_l10n_in_state_id(self):
        res = super()._compute_l10n_in_state_id()
        to_compute = self.filtered(lambda m: m.country_code == 'IN' and not m.l10n_in_state_id and m.journal_id.type == 'general' and m.l10n_in_pos_session_ids)
        for move in to_compute:
            move.l10n_in_state_id = move.company_id.state_id
        return res

    def _post(self, soft=True):
        posted = super()._post(soft)
        for move in posted.filtered(lambda m: m.l10n_in_pos_session_ids and m.move_type == 'entry' and m.country_code == 'IN'):
            move.write({'l10n_in_gstr_json': move.generate_json_data()})
        return posted

    @api.depends('invoice_line_ids', 'invoice_line_ids.tax_ids', 'l10n_in_gst_treatment', 'move_type')
    def _compute_has_nil_exempt_nongst(self):
        taxes_tag_ids = self._get_l10n_in_taxes_tags_id_by_name()
        nil_exempt_nongst_tags = [taxes_tag_ids[key] for key in ['exempt', 'nil_rated', 'non_gst_supplies']]
        for record in self:
            record.has_nil_exempt_nongst = record.l10n_in_gst_treatment not in ('overseas', 'special_economic_zone') \
                and (record.move_type in ('out_invoice', 'out_refund', 'out_receipt') or (record.move_type == 'entry' and record.l10n_in_pos_session_ids))\
                and any(tag in nil_exempt_nongst_tags for tag in record.invoice_line_ids.tax_tag_ids.ids)

    @api.depends('partner_id', 'invoice_line_ids', 'amount_total', 'invoice_line_ids.tax_ids.l10n_in_reverse_charge',
        'move_type', 'state', 'l10n_in_gst_treatment', 'l10n_in_state_id', 'invoice_line_ids.tax_ids', 'debit_origin_id')
    def _compute_gstr_section(self):
        super()._compute_gstr_section()
        taxes_tag_ids = self._get_l10n_in_taxes_tags_id_by_name()
        gst_tags = [taxes_tag_ids[key] for key in ['base_sgst', 'sgst', 'base_cgst', 'cgst', 'base_igst', 'igst', 'base_cess', 'cess']]
        for record in self:
            is_interstate = record.country_code == "IN" and record.l10n_in_state_id and record.l10n_in_state_id != record.company_id.state_id
            is_intrastate = record.country_code == "IN" and record.l10n_in_state_id and record.l10n_in_state_id == record.company_id.state_id
            is_unregistered_or_consumer = record.l10n_in_gst_treatment in ('unregistered', 'consumer')

            if ((record.move_type in ['out_invoice', 'out_receipt', 'out_refund'] and is_unregistered_or_consumer)
                or (record.move_type == 'entry' and (record.l10n_in_pos_session_ids))) \
                and any(tag in gst_tags for tag in record.line_ids.tax_tag_ids.ids) \
                and (is_intrastate or (is_interstate and record.amount_total <= 250000)):
                record.l10n_in_gstr_section = 'b2cs'
