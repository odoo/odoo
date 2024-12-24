# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import float_round, float_repr


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_id_tax_number = fields.Char(string="Tax Number", copy=False)
    l10n_id_replace_invoice_id = fields.Many2one('account.move', string="Replace Invoice", domain="['|', '&', '&', ('state', '=', 'posted'), ('partner_id', '=', partner_id), ('reversal_move_ids', '!=', False), ('state', '=', 'cancel')]", copy=False, index='btree_not_null')
    l10n_id_efaktur_document = fields.Many2one('l10n_id_efaktur.document', readonly=True, copy=False, string="e-Faktur Document")
    l10n_id_kode_transaksi = fields.Selection([
            ('01', '01 To the Parties that is not VAT Collector (Regular Customers)'),
            ('02', '02 To the Treasurer'),
            ('03', '03 To other VAT Collectors other than the Treasurer'),
            ('04', '04 Other Value of VAT Imposition Base'),
            ('05', '05 Specified Amount (Article 9A Paragraph (1) VAT Law)'),
            ('06', '06 Other Deliveries'),
            ('07', '07 Deliveries that the VAT is not Collected'),
            ('08', '08 Deliveries that the VAT is Exempted'),
            ('09', '09 Deliveries of Assets (Article 16D of VAT Law)'),
        ], string='Tax Transaction Code', help='The first 2 digits of tax number',
        readonly=False, copy=False,
        compute="_compute_kode_transaksi", store=True)
    l10n_id_efaktur_range = fields.Many2one("l10n_id_efaktur.efaktur.range", string="E-faktur Range", copy=False, domain="[('company_id', '=', company_id), ('available', '>', 0)]")
    l10n_id_need_kode_transaksi = fields.Boolean(compute='_compute_need_kode_transaksi')
    l10n_id_available_range_count = fields.Integer(compute="_compute_available_range_count", compute_sudo=True)
    l10n_id_show_kode_transaksi = fields.Boolean(compute='_compute_show_kode_transaksi')

    @api.depends('company_id')
    def _compute_available_range_count(self):
        # Only invoices under Indonesian company needs computation for l10n_id_available_range_count
        id_moves = self.filtered(lambda x: x.country_code == 'ID')
        other_moves = self - id_moves

        if other_moves:
            other_moves.l10n_id_available_range_count = 0

        if id_moves:
            range_count_per_company = dict(
                self.env['l10n_id_efaktur.efaktur.range']._read_group(
                    [('available', '>', 0), ('company_id', 'in', id_moves.company_id.ids)],
                    ['company_id'],
                    ['__count']
                )
            )
            for company_id, moves in id_moves.grouped('company_id').items():
                moves.l10n_id_available_range_count = range_count_per_company.get(company_id, 0)

    @api.onchange('l10n_id_tax_number')
    def _onchange_l10n_id_tax_number(self):
        for record in self:
            if record.l10n_id_tax_number and record.move_type not in self.get_purchase_types():
                raise UserError(_("You can only change the number manually for a Vendor Bills and Credit Notes"))

    @api.depends('partner_id')
    def _compute_kode_transaksi(self):
        for move in self:
            move.l10n_id_kode_transaksi = move.partner_id.commercial_partner_id.l10n_id_kode_transaksi

    @api.depends('commercial_partner_id', 'invoice_line_ids.tax_ids')
    def _compute_need_kode_transaksi(self):
        for move in self:
            # If there are no taxes at all on every line (0% taxes counts as having a tax) then we don't need a kode transaksi
            move.l10n_id_need_kode_transaksi = (
                move.commercial_partner_id.l10n_id_pkp
                and not move.l10n_id_tax_number
                and move.move_type == 'out_invoice'
                and move.country_code == 'ID'
                and move.invoice_line_ids.tax_ids
            )

    @api.depends('commercial_partner_id')
    def _compute_show_kode_transaksi(self):
        for move in self:
            move.l10n_id_show_kode_transaksi = (
                move.commercial_partner_id.l10n_id_pkp
                and move.move_type == 'out_invoice'
                and move.country_code == 'ID'
            )

    @api.constrains('l10n_id_kode_transaksi', 'line_ids', 'partner_id')
    def _constraint_kode_ppn(self):
        ppn_tag = self.env.ref('l10n_id.ppn_tag')
        for move in self.filtered(lambda m: m.l10n_id_need_kode_transaksi and m.l10n_id_kode_transaksi != '08'):
            if any(ppn_tag.id in line.tax_tag_ids.ids for line in move.line_ids if line.display_type == 'product') \
                    and any(ppn_tag.id not in line.tax_tag_ids.ids for line in move.line_ids if line.display_type == 'product'):
                raise UserError(_('Cannot mix VAT subject and Non-VAT subject items in the same invoice with this kode transaksi.'))
        for move in self.filtered(lambda m: m.l10n_id_need_kode_transaksi and m.l10n_id_kode_transaksi == '08'):
            if any(ppn_tag.id in line.tax_tag_ids.ids for line in move.line_ids if line.display_type == 'product'):
                raise UserError('Kode transaksi 08 is only for non VAT subject items.')

    @api.constrains('l10n_id_tax_number')
    def _constrains_l10n_id_tax_number(self):
        for record in self.filtered('l10n_id_tax_number'):
            if record.l10n_id_tax_number != re.sub(r'\D', '', record.l10n_id_tax_number):
                record.l10n_id_tax_number = re.sub(r'\D', '', record.l10n_id_tax_number)
            if len(record.l10n_id_tax_number) != 16:
                raise UserError(_('A tax number should have 16 digits'))
            elif record.l10n_id_tax_number[:2] not in dict(self._fields['l10n_id_kode_transaksi'].selection).keys():
                raise UserError(_('A tax number must begin by a valid Kode Transaksi'))
            elif record.l10n_id_tax_number[2] not in ('0', '1'):
                raise UserError(_('The third digit of a tax number must be 0 or 1'))

    def _post(self, soft=True):
        """Set E-Faktur number after validation."""
        for move in self:
            if move.l10n_id_need_kode_transaksi:
                # If the code was set on the partner after the invoice was created, we set it on the move at this step so that it triggers the constrains if needed.
                if not move.l10n_id_kode_transaksi and move.commercial_partner_id.l10n_id_kode_transaksi:
                    move.l10n_id_kode_transaksi = move.commercial_partner_id.l10n_id_kode_transaksi
                if not move.l10n_id_kode_transaksi:
                    raise ValidationError(_('You need to put a Kode Transaksi for this partner.'))
                if move.l10n_id_replace_invoice_id.l10n_id_tax_number:
                    if not move.l10n_id_replace_invoice_id.l10n_id_efaktur_document:
                        raise ValidationError(_('Replacement invoice only for invoices on which the e-Faktur is generated. '))
                    rep_efaktur_str = move.l10n_id_replace_invoice_id.l10n_id_tax_number
                    move.l10n_id_tax_number = '%s1%s' % (move.l10n_id_kode_transaksi, rep_efaktur_str[3:])
                else:
                    # Auto-select the smallest range available
                    if not move.l10n_id_efaktur_range:
                        move.l10n_id_efaktur_range = self.env['l10n_id_efaktur.efaktur.range'].search([('company_id', '=', move.company_id.id), ('available', '>', 0)], order="min ASC", limit=1)
                        if not move.l10n_id_efaktur_range:
                            raise ValidationError(_('There is no Efaktur range available. Please configure the range you get from the government in the e-Faktur Ranges menu. '))
                    efaktur_num = move.l10n_id_efaktur_range.pop_number()
                    move.l10n_id_tax_number = '%s0%013d' % (str(move.l10n_id_kode_transaksi), efaktur_num)
        return super()._post(soft)

    def reset_efaktur(self):
        """Reset E-Faktur, so it can be use for other invoice."""
        for move in self:
            if move.l10n_id_efaktur_document:
                raise UserError(_('You have already generated the tax report for this document: %s', move.name))
            self.env['l10n_id_efaktur.efaktur.range'].push_number(move.company_id.id, move.l10n_id_tax_number[3:])
            move.message_post(
                body='e-Faktur Reset: %s ' % (move.l10n_id_tax_number),
                subject="Reset Efaktur")
            move.l10n_id_tax_number = False
        return True

    def download_csv(self):
        return self.l10n_id_efaktur_document.action_download()

    def download_efaktur(self):
        """Collect the data and execute function _generate_efaktur."""
        for record in self:
            if record.state == 'draft':
                raise ValidationError(_('Could not download E-faktur in draft state'))
            if not record.country_code == 'ID':
                raise ValidationError(_("E-faktur is only available on invoices under Indonesian companies"))
            if not record.partner_id.commercial_partner_id.l10n_id_pkp:
                raise ValidationError(_("E-faktur is only available for taxable customers"))
            if not record.move_type == 'out_invoice':
                raise ValidationError(_("E-faktur is only available for invoices"))
            if not record.line_ids.tax_ids:
                raise ValidationError(_('E-faktur is not available for invoices without any taxes.'))
            if not record.l10n_id_tax_number:
                raise ValidationError(_("Please reset %(move_number)s to draft and post it again to generate the eTax number", move_number=record.name))

        # Should prevent users from generating e-Faktur document on invoices across multi-company.
        # Allowing it will cause issues on the invoice/eFaktur document record rule
        if len(self.company_id) > 1:
            raise UserError(_("You are not allowed to generate e-Faktur document from invoices coming from different companies"))

        # All invoices in self have no documents; we can create a new one for them.
        # Or all invoices in self have a document, but it's the same one. Special use case but we allow downloading it.
        if not self.l10n_id_efaktur_document:
            self.l10n_id_efaktur_document = self.env['l10n_id_efaktur.document'].create({
                'invoice_ids': self.ids,
                'company_id': self.company_id.id,
            })
            self.l10n_id_efaktur_document.action_regenerate()
        # If there is more than one document, or all invoices for a document were not selected, the resulting file could cause mistakes;
        # They could get a file with additional invoices for example. In this case, we redirect them to the document view to make it clearer.
        elif len(self.l10n_id_efaktur_document) > 1 or set(self.l10n_id_efaktur_document.invoice_ids.ids) != set(self.ids):
            action_error = {
                'name': _('Document Mismatch'),
                'view_mode': 'list',
                'res_model': 'l10n_id_efaktur.document',
                'type': 'ir.actions.act_window',
                'views': [[False, 'list'], [False, 'form']],
                'domain': [('id', 'in', self.l10n_id_efaktur_document.ids)],
            }
            msg = _("The selected invoices are partially part of one or more e-faktur documents.\n"
                    "Please download them from the e-faktur documents directly.")
            raise RedirectWarning(msg, action_error, _("Display Related Documents"))

        return self.download_csv()

    def _prepare_etax(self):
        # These values are never set
        return {'JUMLAH_PPNBM': 0, 'UANG_MUKA_PPNBM': 0, 'JUMLAH_BARANG': 0, 'TARIF_PPNBM': 0, 'PPNBM': 0}

    def button_draft(self):
        # EXTENDS 'account'
        # When resetting to draft, we want the invoice to be removed from the document they are linked to.
        # That document will be regenerated when downloading later on with only the remaining invoices.
        invoices_with_document = self.filtered(lambda i: i.l10n_id_efaktur_document)
        if invoices_with_document:
            invoices_document = invoices_with_document.l10n_id_efaktur_document

            invoices_document.attachment_id.unlink()
            invoices_with_document.l10n_id_efaktur_document = False

            empty_documents = invoices_document.filtered(lambda d: not d.invoice_ids)
            # We would like to keep them in case the documents in the chatter are important.
            # Users can always delete them manually as needed.
            if empty_documents:
                empty_documents.active = False

            body = _("This invoice has been unlinked from the e-faktur document %(document_link)s following the reset to draft.",
                     document_link=invoices_document._get_html_link(title=f"{invoices_document.id}"))
            invoices_with_document._message_log_batch(bodies={inv.id: body for inv in invoices_with_document})
        return super().button_draft()
