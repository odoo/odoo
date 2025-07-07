# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import date_utils

from odoo.addons.l10n_my_edi.models.account_edi_xml_ubl_my import E_164_REGEX


class MyInvoisDocumentPoS(models.Model):
    """
    Odoo's support for consolidated invoice is limited to PoS transactions (for now).
    For regular journal entries, they can easily be sent in batch to MyInvois without the need to group them into
    consolidated invoices.

    These consolidated invoices will be linked to PoS orders, with the purpose of sending them at once each
    month during the allowed timeframe.
    An order that has been invoiced separately must not be included in consolidated invoices.

    A single invoice line could represent multiple transactions as long as their numbering is continuous.

    Note that while the xml generation will be using custom python code, the template will be the same as for regular invoices.
    The API endpoints used will also be the same.
    """
    _inherit = 'myinvois.document'

    # ------------------
    # Fields declaration
    # ------------------

    pos_order_ids = fields.Many2many(
        name="Orders",
        comodel_name="pos.order",
        relation="myinvois_document_pos_order_rel",
        column1="document_id",
        column2="order_id",
        check_company=True,
    )
    pos_config_id = fields.Many2one(
        string="PoS Config",
        comodel_name="pos.config",
        readonly=True,
    )
    linked_order_count = fields.Integer(
        compute='_compute_linked_order_count',
    )
    pos_order_date_range = fields.Char(
        string="Date Range",
        compute='_compute_pos_order_date_range',
        store=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    def _compute_linked_order_count(self):
        for consolidated_invoice in self:
            consolidated_invoice.linked_order_count = len(consolidated_invoice.pos_order_ids)

    @api.depends('pos_order_ids')
    def _compute_pos_order_date_range(self):
        for consolidated_invoice in self.filtered('pos_order_ids'):
            first_order = consolidated_invoice.pos_order_ids[-1]
            latest_order = consolidated_invoice.pos_order_ids[0]
            consolidated_invoice.pos_order_date_range = f"{first_order.date_order.date()} to {latest_order.date_order.date()}"

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _get_starting_sequence(self):
        """ In the PoS, a document represents a Consolidated INVoice. """
        self.ensure_one()
        if not self.pos_order_ids:
            return super()._get_starting_sequence()

        return "CINV/%04d/00000" % self.myinvois_issuance_date.year

    # --------------
    # Action methods
    # --------------

    def action_view_linked_orders(self):
        """ Return the action used to open the order(s) linked to the selected consolidated invoice. """
        self.ensure_one()
        if self.linked_order_count == 1:
            action_vals = {
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_mode': 'form',
                'res_id': self.pos_order_ids.id,
                'views': [(False, 'form')],
            }
        else:
            action_vals = {
                'name': self.env._("Point of Sale Orders"),
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', self.pos_order_ids.ids)],
            }

        return action_vals

    def action_open_consolidate_invoice_wizard(self):
        """
        Open the wizard, and set a default date_from/date_to based on the current date as well as already existing
        consolidated invoices.
        """
        latest_consolidated_invoice = self.env['myinvois.document'].search([
            ('company_id', '=', self.env.company.id),
            ('myinvois_state', 'in', ['in_progress', 'valid']),
            ('pos_order_ids', '!=', False),
        ], limit=1)
        if latest_consolidated_invoice:
            default_date_from = latest_consolidated_invoice.myinvois_issuance_date + relativedelta(days=1)
        else:
            default_date_from = date_utils.start_of(fields.Date.context_today(self) - relativedelta(months=1), 'month')
        default_date_to = date_utils.end_of(default_date_from, 'month')

        return {
            'name': self.env._('Create Consolidated Invoice'),
            'res_model': 'myinvois.consolidate.invoice.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'default_date_from': default_date_from,
                'default_date_to': default_date_to,
            },
            'type': 'ir.actions.act_window',
        }

    # ----------------
    # Business methods
    # ----------------

    @api.model
    def _separate_orders_in_lines(self, pos_order_ids):
        """
        Separate the orders in self into lines as represented in a consolidated invoice, taking care of splitting when
        needed.

        There is no requirement asking to split per sequence (and thus config), but we still do so to make it easier to
        submit per PoS if wanted.

        :param pos_order_ids: The orders to separate.
        :return: A list of pos_order record sets, with one record set representing what would go in one line in the xml.
        """
        lines_per_config = {}
        # We start by gathering the sessions involved in this process, and loop on their orders.
        sorted_order = pos_order_ids.sorted(reverse=True)
        all_orders_per_config = sorted_order.session_id.order_ids.sorted(reverse=True).grouped('config_id')
        # During the loop, we want to gather "lines".
        # One line can be comprised of any number of orders as long as they are continuous.
        continuous_orders = self.env['pos.order']
        for config, orders in all_orders_per_config.items():
            config_lines = []
            for order in orders:
                if continuous_orders and order not in pos_order_ids:
                    config_lines.append(continuous_orders)
                    continuous_orders = self.env['pos.order']
                elif order in pos_order_ids:
                    continuous_orders |= order

            # We should group by POS config, as this is where the sequence is expected to be continuous.
            if continuous_orders:
                config_lines.append(continuous_orders)
                continuous_orders = self.env['pos.order']
            lines_per_config[config] = config_lines

        return lines_per_config

    def _myinvois_export_document(self):
        """ Returns a dict with all the values required to build the consolidated invoice XML file. """
        self.ensure_one()

        # We ignore fully refunded orders and orders that are only refunds.
        # In both cases, has_refundable_lines will be False (already refunded OR negative qty)
        orders = self.pos_order_ids.filtered('has_refundable_lines')

        if not orders:
            return super()._myinvois_export_document()

        builder = self.env['account.edi.xml.ubl_myinvois_my']
        # 1. Validate the structure of the taxes
        builder._validate_taxes(orders.lines.tax_ids)
        # 2. Instantiate the XML builder
        vals = {'consolidated_invoice': self.with_context(lang=self.env.company.partner_id.lang)}
        document_node = builder._get_consolidated_invoice_node(vals)
        vals['template'] = document_node
        return vals

    def _myinvois_export_document_constraints(self, xml_vals):
        """ Provides generic constraints that would apply to any documents """
        self.ensure_one()
        constraints = super()._myinvois_export_document_constraints(xml_vals)

        builder = self.env['account.edi.xml.ubl_myinvois_my']
        if not self.company_id.l10n_my_edi_industrial_classification:
            builder._l10n_my_edi_make_validation_error(constraints, 'industrial_classification_required', 'company', self.company_id.display_name)

        # Supplier Check
        supplier = xml_vals['supplier']
        phone_number = supplier.phone or supplier.mobile
        if phone_number != "NA":
            phone = builder._l10n_my_edi_get_formatted_phone_number(phone_number)
            if E_164_REGEX.match(phone) is None:
                builder._l10n_my_edi_make_validation_error(constraints, 'phone_number_format', 'supplier', supplier.display_name)
        elif not phone_number:
            builder._l10n_my_edi_make_validation_error(constraints, 'phone_number_required', 'supplier', supplier.display_name)

        if not supplier.commercial_partner_id.l10n_my_identification_type or not supplier.commercial_partner_id.l10n_my_identification_number:
            builder._l10n_my_edi_make_validation_error(constraints, 'required_id', 'supplier', supplier.commercial_partner_id.display_name)

        if not supplier.state_id:
            builder._l10n_my_edi_make_validation_error(constraints, 'no_state', 'supplier', supplier.display_name)
        if not supplier.city:
            builder._l10n_my_edi_make_validation_error(constraints, 'no_city', 'supplier', supplier.display_name)
        if not supplier.country_id:
            builder._l10n_my_edi_make_validation_error(constraints, 'no_country', 'supplier', supplier.display_name)
        if not supplier.street:
            builder._l10n_my_edi_make_validation_error(constraints, 'no_street', 'supplier', supplier.display_name)

        if supplier.commercial_partner_id.sst_registration_number and len(supplier.commercial_partner_id.sst_registration_number.split(';')) > 2:
            builder._l10n_my_edi_make_validation_error(constraints, 'too_many_sst', 'supplier', supplier.commercial_partner_id.display_name)

        # Line check (based on the vals)
        for line in xml_vals['template']['cac:InvoiceLine']:
            item_vals = line['cac:Item']
            if not item_vals['cac:ClassifiedTaxCategory']:
                builder._l10n_my_edi_make_validation_error(constraints, 'tax_ids_required', line['id'], item_vals['name'])

            for classified_tax_category_val in item_vals['cac:ClassifiedTaxCategory']:
                if classified_tax_category_val['cbc:TaxExemptionReasonCode']['_text'] == 'E' and not classified_tax_category_val['cbc:TaxExemptionReason']['_text']:
                    # We don't have a name here, so the % will have to do
                    builder._l10n_my_edi_make_validation_error(constraints, 'tax_exemption_required_on_tax', classified_tax_category_val['id'], classified_tax_category_val['percent'])

        if all(line['cac:Item']['cac:CommodityClassification']['cbc:ItemClassificationCode']['_text'] == '04' for line in xml_vals['template']['cac:InvoiceLine']):
            # consolidated invoices must use a specific customer VAT number.
            customer_vat = xml_vals['template']['cac:AccountingCustomerParty']['cac:Party']['cac:PartyIdentification'][0]['cbc:ID']['_text']
            if customer_vat != 'EI00000000010':
                builder._l10n_my_edi_make_validation_error(constraints, 'missing_general_public', xml_vals['customer'].id, xml_vals['customer'].name)

        return constraints
