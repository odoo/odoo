# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    ubl_cii_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Attachment",
        compute=lambda self: self._compute_linked_attachment_id('ubl_cii_xml_id', 'ubl_cii_xml_file'),
        depends=['ubl_cii_xml_file']
    )
    ubl_cii_xml_file = fields.Binary(
        attachment=True,
        string="UBL/CII File",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_group_ungroup_lines_by_tax(self):
        """
        This action allows the user to reload an imported move, grouping or not lines by tax
        """
        self.ensure_one()
        self._check_move_for_group_ungroup_lines_by_tax()

        # Check if lines look like they're grouped
        lines_grouped = any(
            re.match(re.escape(self.partner_id.name or _("Unknown partner")) + r' - \d+ - .*', line.name)
            for line in self.line_ids.filtered(lambda x: x.display_type == 'product')
        )

        if lines_grouped:
            self._ungroup_lines()
        else:
            self._group_lines_by_tax()

    def _ungroup_lines(self):
        """
        Ungroup lines using the original file, used to import the move
        """
        error_message = _("Cannot find the origin file, try by importing it again")
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
        ], order='create_date')
        if not attachments:
            raise UserError(error_message)

        success = False
        for file_data in attachments._unwrap_edi_attachments():
            if file_data.get('xml_tree') is None:
                continue
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is None:
                continue
            self.invoice_line_ids = [Command.clear()]
            res = ubl_cii_xml_builder._import_invoice_ubl_cii(self, file_data)
            if res:
                success = True
                self._message_log(body=_("Ungrouped lines from %s", file_data['attachment'].name))
                break
        if not success:
            raise UserError(error_message)

    def _group_lines_by_tax(self):
        """
        Group lines by tax, based on the invoice lines
        """
        line_vals = self._get_line_vals_group_by_tax(self.partner_id, fields.Date.to_string(self.date))
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids = line_vals
        self._message_log(body=_("Grouped lines by tax"))

    def _get_line_vals_group_by_tax(self, partner, date):
        """
        Create a collection of dicts containing the values to create invoice lines, grouped by
        tax and deferred date if present.
        :param partner: partner linked to the move
        :param date: date of the move (string format)
        """
        base_lines = [
            line._convert_to_tax_base_line_dict()
            for line in self.line_ids.filtered(lambda x: x.display_type == 'product')
        ]

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self.env['account.tax']._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        deferred = 'deferred_start_date' in self.env['account.move.line']._fields  # enterprise field

        def grouping_key_generator(base_line, tax_values):
            dates = (False, False)
            record = base_line['record']
            if deferred:
                dates = (record.deferred_start_date, record.deferred_end_date)
            return {'tax': (record.tax_ids, record.account_id, dates)}

        aggregated_lines = self.env['account.tax'].with_company(self.company_id)._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        to_create = []
        for tax_detail in aggregated_lines['tax_details'].values():
            taxes, account, (deferred_start_date, deferred_end_date) = tax_detail['tax']
            vals = {
                'name': " - ".join([partner.name or _("Unknown partner"), account.code, " / ".join([tax.name for tax in taxes]) or _("Untaxed")]),
                'quantity': 1,
                'price_unit': tax_detail['base_amount_currency'],
                'tax_ids': [Command.link(tax.id) for tax in taxes],
                'account_id': account.id,
            }
            if deferred:
                vals.update({'deferred_start_date': deferred_start_date, 'deferred_end_date': deferred_end_date})
            to_create.append(Command.create(vals))

        return to_create

    def _check_move_for_group_ungroup_lines_by_tax(self):
        """
        Perform checks to evaluate if a move is eligible to grouping/ungrouping
        """
        if not self.is_purchase_document(include_receipts=True):
            raise UserError(_("You can only (un)group lines of a incoming invoice (vendor bill)"))
        if self.state != 'draft':
            raise UserError(_("You can only (un)group lines of a draft invoice"))
        # TO REMOVE IN 18.0+ as purchase_edi_ubl_bis module is created
        if 'purchase_order_id' in self.env['account.move.line']._fields:  # purchase field
            if any(line.purchase_order_id for line in self.line_ids):
                raise UserError(_("You can only (un)group lines of an invoice not linked to a purchase order"))

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        ubl_version = tree.find('{*}UBLVersionID')
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text in ('2.1', '2.2', '2.3'):
                return self.env['account.edi.xml.ubl_21']
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0':
                return self.env['account.edi.xml.ubl_a_nz']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0':
                return self.env['account.edi.xml.ubl_sg']
            if 'urn:cen.eu:en16931:2017' in customization_id.text:
                return self.env['account.edi.xml.ubl_bis3']

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'xml':
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is not None:
                return ubl_cii_xml_builder._import_invoice_ubl_cii

        return super()._get_edi_decoder(file_data, new=new)

    def _need_ubl_cii_xml(self):
        self.ensure_one()
        return not self.ubl_cii_xml_id \
            and self.is_sale_document() \
            and bool(self.partner_id.commercial_partner_id.ubl_cii_format)
