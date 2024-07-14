# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_cl_port_origin_id = fields.Many2one(
        comodel_name='l10n_cl.customs_port', string='Port of Origin',
        domain=lambda self: [('country_id', '=', self.env.ref('base.cl').id)],
        help='Choose the port of departure for your goods within the country of origin.')
    l10n_cl_port_destination_id = fields.Many2one(
        comodel_name='l10n_cl.customs_port', string='Port of Destination',
        help='Choose the port where the goods will arrive at the destination country.')
    l10n_cl_destination_country_id = fields.Many2one(
        comodel_name='res.country',
        related='partner_shipping_id.country_id',
        string='Destination Country')
    l10n_cl_customs_quantity_of_packages = fields.Integer(
        string='Quantity of Packages',
        default=1)
    l10n_cl_customs_service_indicator = fields.Selection([
            ('1', 'Periodic domiciliary services'),
            ('2', 'Other periodic services'),
            ('3', 'Services'),
            ('4', 'Hotel services'),
            ('5', 'International land transportation service')],
        string="Customs Service Indicator")
    l10n_cl_customs_transport_type = fields.Selection([
            ('01', 'Maritime, river and lake'),
            ('04', 'Aerial'),
            ('05', 'Post'),
            ('06', 'Railway'),
            ('07', 'Wagoner / Land'),
            ('08', 'Pipelines, Gas Pipelines'),
            ('09', 'Power Line (aerial or underground)'),
            ('10', 'Other'),
            ('11', 'Courier/Air Courier')],
        string='Customs Transport Method')
    l10n_cl_customs_sale_mode = fields.Selection([
            ('1', 'Firmly',),
            ('2', 'Under condition'),
            ('3', 'Under free consignment'),
            ('4', 'Under consignment with a minimum firmly'),
            ('9', 'Without payment')],
        string='Customs sale mode')

    def _l10n_cl_customs_incoterm(self, code):
        incoterm_dict = {
            'CIF': '1',
            'CPT': '11',
            'CIP': '12',
            'DAT': '17',
            'DAP': '18',
            'CFR': '2',
            'EXW': '3',
            'FAS': '4',
            'FOB': '5',
            'S/CL': '6',
            'FCA': '7',
            'DDP': '9',
        }
        return incoterm_dict.get(code, '8')

    def _get_inverse_currency_rate(self):
        return float_round(abs(self.line_ids[0].balance / self.line_ids[0].amount_currency), 2)

    def _l10n_cl_edi_post_validation(self):
        if self.l10n_latam_document_type_id._is_doc_type_export():
            if self.currency_id == self.company_id.currency_id:
                raise UserError(_('You must set a different currency than %s on invoice %s',
                    self.company_id.currency_id.name, self._get_move_display_name()))
        return super()._l10n_cl_edi_post_validation()
