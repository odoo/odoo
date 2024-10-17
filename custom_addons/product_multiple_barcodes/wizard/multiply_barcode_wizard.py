# Copyright 2021 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MultiplyBarcodeWizard(models.TransientModel):
    _name = 'multiply.barcode.wizard'
    _description = 'Update Product Multiply Barcode Wizard'

    name = fields.Char(
        string='New Barcode',
        required=True,
    )

    remember_previous_barcode = fields.Boolean(
        string='Remember previous barcode in "Additional Barcodes" field',
        default=True,
    )

    def update_barcode(self):
        model_name = self.env.context['active_model']
        if model_name == 'product.product':
            product = self.env['product.product'].browse(self.env.context['active_id'])
        if model_name == 'product.template':
            product = self.env['product.template'].browse(
                self.env.context['active_id']
            ).product_variant_id

        if self.remember_previous_barcode:
            barcode = product.barcode            

            if barcode:
                product_barcode_multi = self.env['product.barcode.multi'].create({
                    'name': barcode,
                    'product_id': product.id,
                })

                product.write({
                    'barcode': self.name,
                    'barcode_ids': [(4, product_barcode_multi.id)],
                })

            else:
                product.write({
                    'barcode': self.name
            })

        else:
            product.barcode = self.name
