from urllib.parse import urlencode

from odoo import api, fields, models, _
from odoo.addons.l10n_gr_edi import utils
from odoo.addons.l10n_gr_edi.models.l10n_gr_edi_document import _make_mydata_request
from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    MOVE_PURPOSE_SELECTION,
)
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_greek_company = fields.Boolean(compute='compute_is_greek_company')
    l10n_gr_edi_mark = fields.Char(
        string='Mark',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
    )
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='picking_id',
        copy=False,
        readonly=True,
    )
    l10n_gr_edi_state = fields.Selection(
        selection=[
            ('delivery_note_sent', "Delivery note sent"),
            ('delivery_note_error', "Delivery note send failed"),
        ],
        string="myDATA Status",
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
        tracking=True,
    )
    l10n_gr_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
    )
    l10n_gr_edi_alerts = fields.Json(compute='_compute_l10n_gr_edi_alerts')
    l10n_gr_edi_move_purpose = fields.Selection(
        selection=MOVE_PURPOSE_SELECTION,
        compute='_compute_l10n_gr_edi_move_purpose',
        string="Move Purpose",
        store=True,
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
    l10n_gr_edi_vehicle_number = fields.Char(string="Vehicule number")

    @api.depends('company_id', 'company_id.account_fiscal_country_id', 'company_id.account_fiscal_country_id.code')
    def compute_is_greek_company(self):
        for picking in self:
            picking.is_greek_company = (picking.company_id.account_fiscal_country_id.code == 'GR')

    @api.depends('l10n_gr_edi_document_ids')
    def _compute_from_l10n_gr_edi_document_ids(self):
        self.l10n_gr_edi_state = False
        self.l10n_gr_edi_mark = False
        self.l10n_gr_edi_attachment_id = False

        for picking in self:
            for document in picking.l10n_gr_edi_document_ids.sorted():
                if document.state == 'delivery_note_sent':
                    picking.l10n_gr_edi_state = document.state
                    picking.l10n_gr_edi_mark = document.mydata_mark
                    picking.l10n_gr_edi_attachment_id = document.attachment_id
                    break
            if picking.l10n_gr_edi_document_ids and not picking.l10n_gr_edi_state:
                picking.l10n_gr_edi_state = 'delivery_note_error'

    @api.depends('country_code', 'state')
    def _compute_l10n_gr_edi_alerts(self):
        for picking in self:
            # Warnings are only calculated when the picking state is done.
            # We use `._origin` to make sure the validated picking have all the needed data for validation.
            if picking.is_greek_company and picking.state == 'done':
                picking.l10n_gr_edi_alerts = picking._origin._l10n_gr_edi_get_pre_error_dict()
            else:
                picking.l10n_gr_edi_alerts = False

    @api.depends('is_greek_company')
    def _compute_l10n_gr_edi_move_purpose(self):
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

    @api.onchange('is_greek_company', 'company_id')
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

    @api.onchange('is_greek_company', 'partner_id')
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

    @api.onchange('is_greek_company', 'l10n_gr_edi_vehicle_number')
    def _onchange_l10n_gr_edi_vehicle_number(self):
        for picking in self:
            if not picking.is_greek_company and picking.l10n_gr_edi_vehicle_number:
                picking.l10n_gr_edi_vehicle_number = False

    def _l10n_gr_edi_get_extra_invoice_report_values(self):
        """Get the values used to render the invoice PDF."""
        self.ensure_one()
        document = self.l10n_gr_edi_document_ids.sorted()[:1]

        if document.state == 'delivery_note_sent':
            barcode_params = urlencode({
                'barcode_type': 'QR',
                'quiet': 0,
                'value': document.mydata_url,
                'width': 180,
                'height': 180,
            })
            return {
                'barcode_src': f'/report/barcode/?{barcode_params}',
                'mydata_mark': document.mydata_mark,
            }
        else:
            return {}

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
            'issuer_street': <str | None>,
            'issuer_number': <str | None>,
            'issuer_postal_code': <str | None>,
            'issuer_city': <str | None>,
            'counterpart_vat': <str | None>,
            'counterpart_country': <str | None>,
            'counterpart_branch': <int | None>,
            'counterpart_name': <str | None>,
            'counterpart_postal_code': <str | None>,
            'counterpart_city': <str | None>,
            'counterpart_street': <str | None>,
            'counterpart_number': <str | None>,
            'counterpart_postal_code': <str | None>,
            'counterpart_city': <str | None>,
        }
        :param dict values: dictionary where the address values will be added
        :rtype: dict[str, str|int]
        """
        self.ensure_one()
        street_detail_issuer = utils.street_split(self.company_id.street)
        street_detail_counterpart = utils.street_split(self.partner_id.street)
        values.update({
            'issuer_vat_number': self.company_id.vat.replace('EL', '').replace('GR', ''),
            'issuer_country': self.company_id.country_code,
            'issuer_branch': self.company_id.l10n_gr_edi_branch_number or 0,
            'issuer_name': self.company_id.name.encode('ISO-8859-7'),
            'issuer_street': street_detail_issuer.get('street_name'),
            'issuer_number': street_detail_issuer.get('street_number'),
            'issuer_postal_code': self.company_id.zip,
            'issuer_city': (self.company_id.city or "").encode('ISO-8859-7') or None,
            'counterpart_vat': self.partner_id.vat.replace('EL', '').replace('GR', ''),
            'counterpart_country': self.partner_id.country_code,
            'counterpart_branch': (self.partner_id.l10n_gr_edi_branch_number or 0),
            'counterpart_name': self.partner_id.name.encode('ISO-8859-7'),
            'counterpart_street': street_detail_counterpart.get('street_name'),
            'counterpart_number': street_detail_counterpart.get('street_number'),
            'counterpart_postal_code': self.partner_id.zip,
            'counterpart_city': (self.partner_id.city or "").encode('ISO-8859-7') or None,
        })

    def _l10n_gr_edi_get_pickings_xml_vals(self):
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
                    'icls': [{
                        'category': 'category3',
                        'type': '',
                        'amount': 0,
                    }]
                })

            invoice_values = {
                '__move__': picking,  # will not be rendered; for creating {picking_id -> picking_xml} mapping
                'header_series': '_'.join(picking.name.split('/')[:-1]),
                'header_aa': picking.name.split('/')[-1],
                'header_issue_date': picking.date_done.strftime('%Y-%m-%d'),
                'header_dispatch_time': picking.date_done.strftime('%H:%M:%S'),
                'header_invoice_type': '9.3',
                'header_move_purpose': picking.l10n_gr_edi_move_purpose,
                'header_other_move_purpose_title': picking.l10n_gr_edi_other_move_purpose,
                'header_vehicle_number': picking.l10n_gr_edi_vehicle_number,
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
                'summary_icls': [{
                    'category': 'category3',
                    'type': '',
                    'amount': 0,
                }]
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
        company_required_fields_view = self.env.ref('l10n_gr_edi.view_company_form_inherit_mydata_required_fields')
        partner_required_fields_view = self.env.ref('l10n_gr_edi.view_partner_form_inherit_mydata_required_fields')
        error_action_company = {'action_text': _("View Company"), 'action': self.company_id._get_records_action(name=_("Company"), views=[(company_required_fields_view.id, 'form')])}
        error_action_partner = {'action_text': _("View Partner"), 'action': self.partner_id._get_records_action(name=_("Partner"), views=[(partner_required_fields_view.id, 'form')])}
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
                'message': _("myDATA: You can only send to myDATA from a done delivery order."),
            }
        if not (self.company_id.l10n_gr_edi_aade_id and self.company_id.l10n_gr_edi_aade_key):
            errors['l10n_gr_edi_company_no_cred'] = {
                'message': _("myDATA: You need to set AADE ID and Key in the company settings."),
                **error_action_gr_settings,
            }
        if not (self.company_id.zip and self.company_id.city):
            errors['l10n_gr_edi_company_no_zip_city'] = {
                'message': _("myDATA: Missing city and/or ZIP code on partner %s.", self.partner_id.name),
                **error_action_partner,
            }
        street_detail_issuer = utils.street_split(self.company_id.street)
        if not (street_detail_issuer.get('street_name') and street_detail_issuer.get('street_number')):
            errors['l10n_gr_edi_company_no_street'] = {
            'message': _("myDATA: Missing street and/or street number on company %s.", self.company_id.name),
            **error_action_company,
        }
        if not self.company_id.vat:
            errors['l10n_gr_edi_company_no_vat'] = {
                'message': _("myDATA: Missing VAT on company %s.", self.company_id.name),
                **error_action_company,
            }
        if not self.partner_id:
            errors['l10n_gr_edi_no_partner'] = {
                'message': _("myDATA: Partner must be filled to be able to send to myDATA."),
            }
        if self.partner_id:
            if not self.partner_id.vat:
                errors['l10n_gr_edi_partner_no_vat'] = {
                    'message': _("myDATA: Missing VAT on partner %s.", self.partner_id.name),
                    **error_action_partner,
                }
            if not (self.partner_id.zip and self.partner_id.city):
                errors['l10n_gr_edi_partner_no_zip_city'] = {
                    'message': _("myDATA: Missing city and/or ZIP code on partner %s.", self.partner_id.name),
                    **error_action_partner,
                }
            street_detail_counterpart = utils.street_split(self.partner_id.street)
            if not (street_detail_counterpart.get('street_name') and street_detail_counterpart.get('street_number')):
                errors['l10n_gr_edi_partner_no_street'] = {
                'message': _("myDATA: Missing street and/or street number on partner %s.", self.partner_id.name),
                **error_action_partner,
            }

        for line_no, line in enumerate(self.move_ids, start=1):
            if not line.l10n_gr_edi_measurement_unit:
                errors[f'l10n_gr_edi_{line_no}_missing_uom'] = {
                    'message': _("myDATA: unit of measure on line %s is invalid, please select between 'Units', 'kg', 'L', 'm', 'm²' or 'm³'", line_no),
                }
        return errors

    def _l10n_gr_edi_attach_report_picking(self):
        self.ensure_one()
        report_picking = self.env['ir.actions.report']._render_qweb_pdf('stock.action_report_delivery', self.id)[0]

        attachment = self.env['ir.attachment'].create({
            'name': f"mydata_{self.name.replace('/', '_')}.pdf",
            'type': 'binary',
            'raw': report_picking,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        self.message_post(
            body=_("Delivery note successfuly sent to myDATA"),
            attachment_ids=[attachment.id]
        )

    def _l10n_gr_edi_send_delivery_note(self):
        self.ensure_one()
        xml_vals = self._l10n_gr_edi_get_pickings_xml_vals()
        xml_content = self.env['l10n_gr_edi.document']._l10n_gr_edi_generate_xml_content('l10n_gr_edi.mydata_invoice', xml_vals)
        result = _make_mydata_request(company=self.company_id, endpoint='SendInvoices', xml_content=xml_content)
        self.env['l10n_gr_edi.document']._l10n_gr_edi_handle_send_result(self, result, xml_vals)

        if self.l10n_gr_edi_state == 'delivery_note_error':
            error = _("Error when sending delivery note %s to myDATA:\n\n", self.name)
            error += self.l10n_gr_edi_document_ids.sorted('create_date', reverse=True)[0].message
            raise UserError(error)
        self._l10n_gr_edi_attach_report_picking()

    def l10n_gr_edi_try_send_delivery_note(self):
        self.ensure_one()
        if self._l10n_gr_edi_get_pre_error_dict():
            raise ValidationError(_("Please resolve all warnings before sending the Delivery Note to myDATA."))
        else:
            self.env['res.company']._with_locked_records(self)
            self._l10n_gr_edi_send_delivery_note()
