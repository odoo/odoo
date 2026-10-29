# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
try:
    import qrcode
except ImportError:
    qrcode = None
try:
    import base64
except ImportError:
    base64 = None
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Partners(models.Model):
    """Extends the res.partner model to include QR code functionality."""
    _inherit = 'res.partner'

    sequences = fields.Char(string="QR Sequence", readonly=True)
    qr = fields.Binary(string="QR Code")

    def init(self):
        """Initialize the QR sequence for customer partners with a combination
        of 'DEF', partner's name (without spaces), and partner's ID."""
        for record in self.env['res.partner'].search(
                [('customer_rank', '=', True)]):
            name = record.name.replace(" ", "")
            print(name,'ssssssssssssssssssssss')
            print(str(record.id),type(record.id),'cxxxxxxxxxxxxxxxxxxxx')
            record.sequences = 'DEF' + name.upper() + str(record.id)
            print(record.sequences,'ccccccccccccccc',type(record.sequences))

    @api.model
    def create(self, vals):
        """Create a new partner record and assign a unique QR sequence to it."""
        prefix = self.env['ir.config_parameter'].sudo().get_param(
            'customer_product_qr.config.customer_prefix')
        if not prefix:
            raise UserError(_('Set A Customer Prefix In General Settings'))
        prefix = str(prefix)
        seq = prefix + self.env['ir.sequence'].next_by_code(
            'res.partner') or '/'
        vals['sequences'] = seq
        return super(Partners, self).create(vals)

    @api.depends('sequences')
    def generate_qr(self):
        """Generate a QR code based on the partner's sequence and store it in
        the 'qr' field of the partner record."""
        if qrcode and base64:
            if not self.sequences:
                prefix = self.env['ir.config_parameter'].sudo().get_param(
                    'customer_product_qr.config.customer_prefix')
                if not prefix:
                    raise UserError(
                        _('Set A Customer Prefix In General Settings'))
                prefix = str(prefix)
                self.sequences = prefix + self.env['ir.sequence'].next_by_code(
                    'res.partner') or '/'
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.sequences)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.write({'qr': qr_image})
            return self.env.ref(
                'customer_product_qrcode.print_qr').report_action(self, data={
                'data': self.id, 'type': 'cust'})
        else:
            raise UserError(
                _('Necessary Requirements To Run This Operation Is Not Satisfied'))

    def get_partner_by_qr(self, **args):
        return self.env['res.partner'].search([('sequences', '=', self.id), ],
                                              limit=1).id


class Products(models.Model):
    """Extends the product.product model to include QR code functionality."""
    _inherit = 'product.product'

    sequences = fields.Char(string="QR Sequence", readonly=True)
    qr = fields.Binary(string="QR Code")

    @api.model
    def create(self, vals):
        """Create a new product and assign a unique QR sequence and QR code
        to it."""
        prefix = self.env['ir.config_parameter'].sudo().get_param(
            'customer_product_qr.config.product_prefix')
        if not prefix:
            raise UserError(_('Set A Product Prefix In General Settings'))
        prefix = str(prefix)
        seq = prefix + self.env['ir.sequence'].next_by_code(
            'product.product') or '/'
        vals['sequences'] = seq
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(vals['sequences'])
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        vals.update({'qr': qr_image})
        return super(Products, self).create(vals)

    @api.depends('sequences')
    def generate_qr(self):
        """Generate a QR code based on the product's sequence and store it in
        the 'qr' field of the product."""
        if qrcode and base64:
            if not self.sequences:
                prefix = self.env['ir.config_parameter'].sudo().get_param(
                    'customer_product_qr.config.product_prefix')
                if not prefix:
                    raise UserError(
                        _('Set A Customer Prefix In General Settings'))
                prefix = str(prefix)
                self.sequences = prefix + self.env['ir.sequence'].next_by_code(
                    'product.product') or '/'
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.sequences)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.write({'qr': qr_image})
            return self.env.ref(
                'customer_product_qrcode.print_qr2').report_action(self, data={
                'data': self.id, 'type': 'prod'})
        else:
            raise UserError(
                _('Necessary Requirements To Run This Operation Is Not Satisfied'))

    def get_product_by_qr(self, **args):
        """Retrieve a product based on the provided QR sequence."""
        return self.env['product.product'].search(
            [('sequences', '=', self.id), ], limit=1).id


class ProductTemplate(models.Model):
    """Extends the product.template model to generate QR codes for all
    related product variants."""
    _inherit = 'product.template'

    def generate_qr(self):
        """Generate QR codes for all product variants associated with the
        product template."""
        product = self.env['product.product'].search(
            [('product_tmpl_id', '=', self.id), ])
        for rec in product:
            rec.generate_qr()
        return self.env.ref('customer_product_qrcode.print_qr2').report_action(
            self, data={'data': self.id, 'type': 'all'})


class ResConfigSettings(models.TransientModel):
    """Extends the res.config.settings model to include configuration
    settings for QR code prefixes."""
    _inherit = 'res.config.settings'

    customer_prefix = fields.Char(string="Customer QR Prefix")
    product_prefix = fields.Char(string="Product QR Prefix")

    def get_values(self):
        """fRetrieve the current configuration values for QR code prefixes."""
        res = super(ResConfigSettings, self).get_values()
        customer_prefix = self.env["ir.config_parameter"].get_param(
            "customer_product_qr.config.customer_prefix")
        product_prefix = self.env["ir.config_parameter"].get_param(
            "customer_product_qr.config.product_prefix")
        res.update({
            'customer_prefix': customer_prefix if type(
                customer_prefix) else False,
            'product_prefix': product_prefix if type(product_prefix) else False
        }
        )
        return res

    def set_values(self):
        """Set the configuration values for QR code prefixes."""
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_product_qr.config.customer_prefix', self.customer_prefix)
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_product_qr.config.product_prefix', self.product_prefix)
        super(ResConfigSettings, self).set_values()
