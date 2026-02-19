# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions  (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models


class HospitalPharmacy(models.Model):
    """Class holding Pharmacy details."""
    _name = 'hospital.pharmacy'
    _description = 'Pharmacy'

    name = fields.Char(string="Name", help='Name of the pharmacy',
                       required="True")
    pharmacist_id = fields.Many2one('hr.employee',
                                    string="Pharmacist",
                                    help='Name of the pharmacist',
                                    domain=[
                                        ('job_id.name', '=', 'Pharmacist')])
    phone = fields.Char(string='Phone', help='Phone number of the pharmacy')
    mobile = fields.Char(string='Mobile', help='Mobile number of the pharmacy')
    email = fields.Char(string='Email', help='Email of the pharmacy')
    street = fields.Char(string='Street', help='Street of pharmacy')
    street2 = fields.Char(string='Street2', help='Street2 of pharmacy')
    zip = fields.Char(string='Zip', help='Zip code of pharmacy')
    city = fields.Char(string='City', help='City of pharmacy')
    state_id = fields.Many2one("res.country.state", string='State',
                               help='State of pharmacy')
    country_id = fields.Many2one('res.country', string='Country',
                                 help='Country of pharmacy')
    notes = fields.Text(string='Notes', help='Notes regarding pharmacy')
    image_129 = fields.Image(string='Image', help='Image of pharmacy',
                             max_width=128, max_height=128)
    active = fields.Boolean(string='Active', help='True for active pharmacy',
                            default=True)
    medicine_ids = fields.One2many('pharmacy.medicine',
                                   'pharmacy_id',
                                   string='Pharmacy',
                                   help='Indicates the medicines in the '
                                        'pharmacy')
    sales_team_id = fields.Many2one('crm.team', string='Sales Team',
                                    help='Choose the sales-team for the'
                                         ' pharmacy')

    @api.model
    def create(self, vals):
        """Method for creating CRM team"""
        team_id = self.env['crm.team'].sudo().create({
            'name': vals['name'] + ' Pharmacy Team',
            'company_id': False,
            'user_id': self.env.uid
        })
        vals['sales_team_id'] = team_id.id
        return super().create(vals)

    @api.model
    def create_sale_order(self, **kwargs):
        """Creating sale order from pharmacy dashboard"""
        if 'op' not in kwargs.keys():
            patient_id = self.env['res.partner'].sudo().create({
                'name': kwargs['name'],
            })
        else:
            patient_id = self.env['hospital.outpatient'].sudo().search(
                [('op_reference', '=', kwargs['op'])]).patient_id
        pharmacy_sale_order = self.env['sale.order'].sudo().create({
            'partner_id': patient_id.id,
        })
        for rec in kwargs['products']:
            pharmacy_sale_order.sudo().write({
                'order_line': [(0, 0, {
                    'product_id': int(
                        rec['prod']) if 'op' not in kwargs.keys() else
                    self.env[
                        'product.product'].search(
                        [('product_tmpl_id', '=', int(rec['prod']))]).id,
                    'product_uom_qty': float(rec['qty']),
                    'price_unit': float(
                        rec['price']) if 'price' in rec.keys() else
                    self.env[
                        'product.product'].search(
                        [('product_tmpl_id', '=',
                          int(rec['prod']))]).list_price
                })]
            })
        pharmacy_sale_order.action_confirm()
        if 'op' in kwargs.keys():
            self.env['hospital.outpatient'].sudo().search(
                [('op_reference', '=', kwargs['op'])]).write(
                {
                    'is_sale_created': True
                })
        return pharmacy_sale_order

    @api.model
    def company_currency(self):
        """Currency symbol of current company"""
        return self.env.user.company_id.currency_id.symbol

    @api.model
    def tax_amount(self, kw):
        """Amount in tax of selected product in pharmacy"""
        return {
            'amount': self.env['account.tax'].sudo().browse(kw).amount
        }

    def action_get_inventory(self):
        """Inventory adjustment for medicine"""
        med_list = []
        for med in self.medicine_ids.product_id:
            for product in self.env['product.product'].sudo().search([]):
                if med.id == product.product_tmpl_id.id:
                    med_list.append(product.id)
        return {
            'name': 'medicine',
            'domain': ['&', ('product_id', 'in', med_list),
                       ('location_id.usage', '=', 'internal')],
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_id': self.env.ref(
                'stock.view_stock_quant_tree_inventory_editable').id,
            'view_mode': 'tree',
        }

    def action_get_sale_order(self):
        """Sale order view of medicine"""
        return {
            'name': 'Sales',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('team_id', '=', self.sales_team_id.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_team_id': self.sales_team_id.id}
        }

    def fetch_sale_orders(self):
        """Method to fetch all sale orders for displaying on pharmacy
        dashboard"""
        return self.env['sale.order'].search_read(
            [('partner_id.patient_seq', 'not in', ['New', 'Employee',
                                                   'User'])],
            fields=['name', 'create_date', 'partner_id', 'amount_total',
                    'state'])
