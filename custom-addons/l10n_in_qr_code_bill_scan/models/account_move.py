import jwt
import json
from datetime import datetime

from odoo import api, Command, models, _

MOVE_TYPE_MAPPING = {
    'INV': 'in_invoice',
    'CRN': 'in_refund',
    'DBN': 'in_invoice'
}

class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_in_get_notification_action(self, params):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': params,
        }

    @api.model
    def l10n_in_get_bill_from_qr_raw(self, qr_raw):
        try:
            qr_json = jwt.decode(qr_raw, options={'verify_signature': False})
        except jwt.exceptions.DecodeError:
            return self._l10n_in_get_notification_action({'type': 'danger', 'message': _("Scanned QR it's not E-Invoice QR code. Please scan E-invoice QR code")})
        qr_json_data = json.loads(qr_json.get('data', '{}'))
        is_valid = self._l10n_in_validate_qr_data(qr_json_data)
        if not is_valid:
            message = _("Scanned QR Code is not appropriate as per E-Invoice QR")
            return self._l10n_in_get_notification_action({'type': 'danger', 'message': message})
        default_journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id)], limit=1)
        bill_action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        bill_action.update({
            'views': [[False, "form"]],
            'context': {
                'create': False, # If new button is clicked then below default values will be set again.
                'default_ref': qr_json_data.get('DocNo'),
                'default_journal_id': default_journal.id,
                'default_invoice_date': datetime.strptime(qr_json_data.get('DocDt'), "%d/%m/%Y"),
                'default_move_type': MOVE_TYPE_MAPPING.get(qr_json_data.get('DocTyp')),
                'default_partner_id': self._l10n_in_get_partner_from_gstin(qr_json_data.get('SellerGstin')),
                'default_invoice_line_ids': self.env.company.extract_single_line_per_tax and [
                    Command.create(self._l10n_in_get_move_lines_vals_from_qr_data(default_journal, qr_json_data))] or [],
            }
        })
        return bill_action

    @api.model
    def _l10n_in_get_move_lines_vals_from_qr_data(self, journal, qr_data):
        price_unit = qr_data.get('TotInvVal')
        move_line_vals = {
            'name': _('HSN: %s', qr_data.get('MainHsnCode')),
            'quantity': 1,
            'price_unit': price_unit,
            'account_id': journal.default_account_id.id,
        }
        products = self.env['product.product'].search([('l10n_in_hsn_code', '=', qr_data.get('MainHsnCode'))], limit=2)
        if products:
            taxes = products[0].supplier_taxes_id # Same HSN code -> same taxes
            if taxes:
                taxes_on_line = igst_taxes = taxes
                fiscal_position = self.env.ref(f'account.{self.env.company.id}_fiscal_position_in_inter_state', raise_if_not_found=False)
                if fiscal_position:
                    # The tax computation of taxes i.e. GST 5%, GST 18%, etc.
                    # the `total_exluded` value is computed incorrectly because of
                    # two sub-taxes i.e. SGST and CGST because the tax amount of the first tax
                    # is added to the next tax base value, it is better to use IGST for `total_exluded` value computation
                    igst_taxes = fiscal_position.map_tax(igst_taxes)
                    # If the supplier and the buyer are from different states then IGST will be applied
                    if qr_data.get('SellerGstin')[0:2] != qr_data.get('BuyerGstin')[0:2]:
                        taxes_on_line = igst_taxes
                computed_tax = igst_taxes.filtered(lambda tax: not any(tax.flatten_taxes_hierarchy().mapped('price_include'))
                    ).with_context(force_price_include=True).compute_all(price_unit=price_unit)
                move_line_vals.update({
                    'price_unit': computed_tax.get('total_excluded'),
                    'tax_ids': [Command.set(taxes_on_line.ids)],
                })
            if len(products) == 1:
                move_line_vals.update({'product_id': products.id})
        return move_line_vals

    @api.model
    def _l10n_in_qr_scan_get_partner_vals_by_vat(self, vat):
        partner_details = self.env['res.partner'].read_by_vat(vat)
        if partner_details:
            partner_data = partner_details[0]
            if partner_data.get('partner_gid'):
                partner_data = self.env['res.partner'].enrich_company(company_domain=None, partner_gid=partner_data.get('partner_gid'), vat=partner_data.get('vat'))
                partner_data = self.env['res.partner']._iap_replace_logo(partner_data)
            return {
                'name': partner_data.get('name'),
                'company_type': 'company',
                'partner_gid': partner_data.get('partner_gid'),
                'vat': partner_data.get('vat'),
                'l10n_in_gst_treatment': 'regular',
                'image_1920': partner_data.get('image_1920'),
                'street': partner_data.get('street'),
                'street2': partner_data.get('street2'),
                'city': partner_data.get('city'),
                'zip': partner_data.get('zip'),
            }
        return {}

    def _l10n_in_get_partner_from_gstin(self, gstin):
        partner = self.env['res.partner']._retrieve_partner(vat=gstin)
        if partner:
            return partner.id
        partner_vals = self._l10n_in_qr_scan_get_partner_vals_by_vat(gstin)
        if partner_vals:
            partner = self.env['res.partner'].create(partner_vals)
            #read_by_vat method is not providing the state/country code
            #by using the following methods the state and country will set from the partner vat
            partner.onchange_vat()
            partner._onchange_state()
            return partner.id
        return False

    @api.model
    def _l10n_in_validate_qr_data(self, qr_data):
        return all(key in qr_data for key in ["DocNo", "SellerGstin", "TotInvVal", "DocDt", "DocTyp", "MainHsnCode"])
