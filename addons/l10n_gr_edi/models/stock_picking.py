from odoo import api, fields, models
from odoo.addons.l10n_gr_edi import utils
from odoo.addons.l10n_gr_edi.models.l10n_gr_edi_document import _make_mydata_request
from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    MOVE_PURPOSE_SELECTION,
    # TYPES_WITH_FORBIDDEN_AMOUNT,
    # TYPES_WITH_MANDATORY_ISSUER,
    # TYPES_WITH_MANDATORY_ITEM_DESCR,
)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_greek_company = fields.Boolean(compute='compute_is_greek_company')
    l10n_gr_edi_mark = fields.Char(
        string='Mark',
        # compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
    )
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='picking_id',
        copy=False,
        readonly=True,
    )
    # l10n_gr_edi_state = fields.Selection(
    #     selection=[
    #         ('invoice_sent', 'Invoice sent'),
    #         ('bill_fetched', "Expense classification ready to send"),
    #         ('bill_sent', "Expense classification sent"),
    #     ],
    #     string='myDATA Status',
    #     compute='_compute_from_l10n_gr_edi_document_ids',
    #     store=True,
    #     tracking=True,
    # )
    # l10n_gr_edi_attachment_id = fields.Many2one(
    #     comodel_name='ir.attachment',
    #     compute='_compute_from_l10n_gr_edi_document_ids',
    #     store=True,
    # )
    l10n_gr_edi_note_is_sent = fields.Boolean()
    l10n_gr_edi_move_purpose = fields.Selection(
        selection=MOVE_PURPOSE_SELECTION,
    )
    l10n_gr_edi_other_move_purpose = fields.Char()
    l10n_gr_edi_loading_address_street = fields.Char()
    l10n_gr_edi_loading_address_number = fields.Char()
    l10n_gr_edi_loading_address_zip = fields.Char()
    l10n_gr_edi_loading_address_city = fields.Char()
    l10n_gr_edi_delivery_address_street = fields.Char()
    l10n_gr_edi_delivery_address_number = fields.Char()
    l10n_gr_edi_delivery_address_zip = fields.Char()
    l10n_gr_edi_delivery_address_city = fields.Char()
    l10n_gr_edi_is_courier_delivery = fields.Boolean(string="Is delivered by courier")
    l10n_gr_edi_vehicule_number = fields.Char(string="Vehicule number")

    @api.depends('company_id.account_fiscal_country_id.code')
    def compute_is_greek_company(self):
        for picking in self:
            picking.is_greek_company = (picking.company_id.account_fiscal_country_id.code == 'GR')

    # @api.depends('l10n_gr_edi_document_ids')
    # def _compute_from_l10n_gr_edi_document_ids(self):
    #     self.l10n_gr_edi_state = False
    #     self.l10n_gr_edi_mark = False
    #     self.l10n_gr_edi_cls_mark = False
    #     self.l10n_gr_edi_attachment_id = False

    #     for picking in self:
    #         for document in picking.l10n_gr_edi_document_ids.sorted():
    #             if document.state in ('invoice_sent', 'bill_fetched', 'bill_sent'):
    #                 picking.l10n_gr_edi_state = document.state
    #                 picking.l10n_gr_edi_mark = document.mydata_mark
    #                 picking.l10n_gr_edi_cls_mark = document.mydata_cls_mark
    #                 picking.l10n_gr_edi_attachment_id = document.attachment_id
    #                 break

    @api.onchange('is_greek_company')
    def _onchange_l10n_gr_edi_move_purpose(self):
        for picking in self:
            if picking.is_greek_company:
                picking.l10n_gr_edi_move_purpose = '1'
            else:
                picking.l10n_gr_edi_move_purpose = False

    @api.onchange('l10n_gr_edi_move_purpose')
    def _onchange_l10n_gr_edi_other_move_purpose(self):
        for picking in self:
            if picking.l10n_gr_edi_move_purpose != '19' and picking.l10n_gr_edi_other_move_purpose:
                picking.l10n_gr_edi_other_move_purpose = False

    @api.onchange('is_greek_company', 'company_id.street', 'company_id.zip', 'company_id.city')
    def _onchange_l10n_gr_edi_loading_address(self):
        for picking in self:
            if picking.state == 'done':
                pass
            if picking.is_greek_company:
                street_detail = utils.street_split(picking.company_id.street)
                picking.l10n_gr_edi_loading_address_street = street_detail.get('street_name')
                picking.l10n_gr_edi_loading_address_number = street_detail.get('street_number')
                picking.l10n_gr_edi_loading_address_zip = picking.company_id.zip or ""
                picking.l10n_gr_edi_loading_address_city = picking.company_id.city or ""
            else:
                picking.l10n_gr_edi_loading_address_street = False
                picking.l10n_gr_edi_loading_address_number = False
                picking.l10n_gr_edi_loading_address_zip = False
                picking.l10n_gr_edi_loading_address_city = False

    @api.onchange('is_greek_company', 'partner_id', 'partner_id.street', 'partner_id.zip', 'partner_id.city')
    def _onchange_l10n_gr_edi_delivery_address(self):
        for picking in self:
            if picking.state == 'done':
                pass
            if picking.is_greek_company:
                street_detail = utils.street_split(picking.partner_id.street)
                picking.l10n_gr_edi_delivery_address_street = street_detail.get('street_name')
                picking.l10n_gr_edi_delivery_address_number = street_detail.get('street_number')
                picking.l10n_gr_edi_delivery_address_zip = picking.partner_id.zip or ""
                picking.l10n_gr_edi_delivery_address_city = picking.partner_id.city or ""
            else:
                picking.l10n_gr_edi_delivery_address_street = False
                picking.l10n_gr_edi_delivery_address_number = False
                picking.l10n_gr_edi_delivery_address_zip = False
                picking.l10n_gr_edi_delivery_address_city = False

    @api.onchange('l10n_gr_edi_is_delivered_by_courier')
    def _onchange_l10n_gr_edi_vehicule_number(self):
        for picking in self:
            if not picking.is_greek_company or picking.l10n_gr_edi_is_delivered_by_courier:
                picking.l10n_gr_edi_vehicule_number = False

    def _l10n_gr_edi_add_address_vals(self, values):
        """
        Adds all the address values needed for the ``invoice_vals`` dictionary.
        The only guaranteed keys in to add in the dictionary is the issuer's VAT, country code, and branch number.
        Everything else is only displayed on some specific case/configuration.
        The appended dictionary will have the following additional keys:
        {
            'issuer_vat_number': <str>,
            'issuer_country': <str>,
            'issuer_branch': <int>,
            'issuer_name': <str | None>,
            'issuer_postal_code': <str | None>,
            'issuer_city': <str | None>,
            'counterpart_vat': <str | None>,
            'counterpart_country': <str | None>,
            'counterpart_branch': <int | None>,
            'counterpart_name': <str | None>,
            'counterpart_postal_code': <str | None>,
            'counterpart_city': <str | None>,
            'counterpart_postal_code': <str | None>,
            'counterpart_city': <str | None>,
        }
        :param dict values: dictionary where the address values will be added
        :rtype: dict[str, str|int]
        """
        self.ensure_one()
        conditional_address_keys = ('issuer_name', 'issuer_postal_code', 'issuer_city', 'counterpart_vat', 'counterpart_country',
                                    'counterpart_branch', 'counterpart_name', 'counterpart_postal_code', 'counterpart_city')
        street_detail_issuer = utils.street_split(self.company_id.street)
        street_detail_counterpart = utils.street_split(self.commercial_partner_id.street)
        values.update({
            'issuer_vat_number': self.company_id.vat.replace('EL', '').replace('GR', ''),
            'issuer_country': self.company_id.country_code,
            'issuer_branch': self.company_id.l10n_gr_edi_branch_number or 0,
            'issuer_name': self.company_id.name.encode('ISO-8859-7'),
            'issuer_street': street_detail_issuer.get('street_name'),
            'issuer_number': street_detail_issuer.get('street_number'),
            'issuer_postal_code': self.company_id.zip,
            'issuer_city': (self.company_id.city or "").encode('ISO-8859-7') or None,
            'counterpart_vat': self.commercial_partner_id.vat.replace('EL', '').replace('GR', ''),
            'counterpart_country': self.commercial_partner_id.country_code,
            'counterpart_branch': (self.commercial_partner_id.l10n_gr_edi_branch_number or 0),
            'counterpart_street': street_detail_counterpart.get('street_name'),
            'counterpart_number': street_detail_counterpart.get('street_number'),
            'counterpart_postal_code': self.commercial_partner_id.zip,
            'counterpart_city': (self.commercial_partner_id.city or "").encode('ISO-8859-7') or None,
            **dict.fromkeys(conditional_address_keys),
        })
        if partner_not_from_greece:
            values['counterpart_name'] = self.commercial_partner_id.name.encode('ISO-8859-7')

    def _l10n_gr_edi_get_invoices_xml_vals(self):
        """
        Generates a dictionary containing the values needed for rendering ``l10n_gr_edi.mydata_invoice`` XML.
        :return: dict
        """
        xml_vals = {'invoice_values_list': []}

        for picking in self.sorted(key='id'):
            details = []

            for line_no, line in enumerate(picking.move_ids, start=1):
                details.append({
                    'line_number': line_no,
                    'quantity': line.quantity,
                    'unit_of_measure': line.l10n_gr_edi_measurement_unit,
                    'item_description': line.product_id.name,
                    'net_value': 0,
                    'vat_amount': 0,
                    'vat_category': 8,
                })

            invoice_values = {
                '__picking__': picking,  # will not be rendered; for creating {picking_id -> picking_xml} mapping
                'header_series': '_'.join(picking.name.split('/')[:-1]),
                'header_aa': picking.name.split('/')[-1],
                'header_issue_date': picking.date.isoformat(),
                'header_invoice_type': '9.3',
                'move_purpose': picking.l10n_gr_edi_picking_purpose,
                'other_move_purpose_title': picking.l10n_gr_edi_other_move_purpose,
                'vehicule_number': picking.l10n_gr_edi_vehicule_number,
                'loading_street': picking.l10n_gr_edi_loading_address_street,
                'loading_number': picking.l10n_gr_edi_loading_address_number,
                'loading_postal_code': picking.l10n_gr_edi_loading_address_zip,
                'loading_city': picking.l10n_gr_edi_loading_address_city,
                'delivery_street': picking.l10n_gr_edi_delivery_address_street,
                'delivery_number': picking.l10n_gr_edi_delivery_address_number,
                'delivery_postal_code': picking.l10n_gr_edi_delivery_address_zip,
                'delivery_city': picking.l10n_gr_edi_delivery_address_city,
                'details': details,
                'summary_total_net_value': 0,
                'summary_total_vat_amount': 0,
                'summary_total_withheld_amount': 0,
                'summary_total_fees_amount': 0,
                'summary_total_stamp_duty_amount': 0,
                'summary_total_other_taxes_amount': 0,
                'summary_total_deductions_amount': 0,
                'summary_total_gross_value': 0,
            }
            picking._l10n_gr_edi_add_address_vals(invoice_values)
            xml_vals['invoice_values_list'].append(invoice_values)

        return xml_vals

    def _l10n_gr_edi_get_pre_error_dict(self):
        """
        Try to catch all possible errors before sending to myDATA.
        Returns an error dictionary in the format of Actionable Error JSON.
        """
        self.ensure_one()
        errors = {}
        error_action_company = {'action_text': _("View Company"), 'action': self.company_id._get_records_action(name=_("Company"))}
        error_action_partner = {'action_text': _("View Partner"), 'action': self.partner_id._get_records_action(name=_("Partner"))}
        error_action_gr_settings = {
            'action_text': _("View Settings"),
            'action': {
                'name': _("Settings"),
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': '/odoo/settings#l10n_gr_edi_aade_settings',
            },
        }

        if self.state != 'done':
            errors['l10n_gr_edi_picking_not_done'] = {
                'message': _("You can only send to myDATA from a done delivery order."),
            }
        if not (self.company_id.l10n_gr_edi_aade_id and self.company_id.l10n_gr_edi_aade_key):
            errors['l10n_gr_edi_company_no_cred'] = {
                'message': _("You need to set AADE ID and Key in the company settings."),
                **error_action_gr_settings,
            }
        street_detail_issuer = utils.street_split(self.company_id.street)
        if not (street_detail_issuer.get('street_name') and street_detail_issuer.get('street_number')):
            errors['l10n_gr_edi_partner_no_street'] = {
            'message': _("Missing street and/or street number on company %s.", self.company_id.name),
            **error_action_company,
        }
        if not self.company_id.vat:
            errors['l10n_gr_edi_company_no_vat'] = {
                'message': _("Missing VAT on company %s.", self.company_id.name),
                **error_action_company,
            }
        if not self.partner_id:
            errors['l10n_gr_edi_no_partner'] = {
                'message': _("Partner must be filled to be able to send to myDATA."),
            }
        if self.partner_id:
            if not self.partner_id.vat:
                errors['l10n_gr_edi_partner_no_vat'] = {
                    'message': _("Missing VAT on partner %s.", self.partner_id.name),
                    **error_action_partner,
                }
            if not (self.partner_id.zip and self.partner_id.city):
                errors['l10n_gr_edi_partner_no_zip_cityt'] = {
                    'message': _("Missing city and/or ZIP code on partner %s.", self.partner_id.name),
                    **error_action_partner,
                }
            street_detail_counterpart = utils.street_split(self.partner_id.street)
            if not (street_detail_counterpart.get('street_name') and street_detail_counterpart.get('street_number')):
                errors['l10n_gr_edi_partner_no_street_nb'] = {
                'message': _("Missing street and/or street number on partner %s.", self.partner_id.name),
                **error_action_partner,
            }

        for line_no, line in enumerate(self.move_ids, start=1):
            if not line.l10n_gr_edi_measurement_unit:
                errors[f'l10n_gr_edi_{line_no}_missing_uom'] = {
                    'message': _("myDATA does not accept the unit on line %s, please select between 'kg', 'L' or 'Units'", line_no),
                }
        return errors

    def _l10n_gr_edi_send_delivery_note(self):
        for company, pickings in self.grouped('company_id').items():
            xml_vals = pickings._l10n_gr_edi_get_pickings_xml_vals()
            xml_content = self.env['account.move']._l10n_gr_edi_generate_xml_content('l10n_gr_edi.mydata_invoice', xml_vals)
            result = _make_mydata_request(company=company, endpoint='SendInvoices', xml_content=xml_content)
            self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def action_l10n_gr_edi_try_send_delivery_note(self):
        pickings_to_send = self.env['stock.picking']
        for picking in self:
            if error := picking._l10n_gr_edi_get_pre_error_dict():
                picking._l10n_gr_edi_create_error_document({'error': utils.get_pre_error_string(error)})
            else:
                pickings_to_send |= picking

        if pickings_to_send:
            self.env['res.company']._with_locked_records(pickings_to_send)
            pickings_to_send._l10n_gr_edi_send_delivery_note()
