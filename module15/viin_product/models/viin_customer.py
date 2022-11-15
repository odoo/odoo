from odoo import fields, models


class ViinCustomer(models.Model):
    _name = 'viin.customer'
    _description = 'Viin Customer'
    name = fields.Char(string='Last name', required=True, translate=True , help="Enter the last name")
    image = fields.Image(string='Customer image')
    phone = fields.Char(string='Phone number', help="Enter the phone number")
    address = fields.Text(string='address', translate=True , help="Enter the address")
    note = fields.Text(string='Note', translate=True )
    
    order_ids = fields.One2many('viin.order', 'customer_id', string='orders')

   

   
   
    
    

