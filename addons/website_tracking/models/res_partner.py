# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo import api, fields, models, tools


class ResPartner(models.Model):
    _inherit = 'res.partner'

    product_view_ids = fields.One2many('product.view', 'res_partner_id', string='Last 10 products viewed')

class ProductView(models.Model):
    _name = "product.view"
    _description = "Keep track of the products viewed by a partner."

    res_partner_id = fields.Many2one('res.partner', index=True, ondelete='cascade', required=True)
    product_template_id = fields.Many2one('product.template', index=True, ondelete='cascade', required=True)
    last_product_id = fields.Many2one('product.product', ondelete='cascade')

    _sql_constraints = [
        ('unique_product_per_partner', 'UNIQUE (res_partner_id, product_template_id)', 'Tuple res_partner_id/product_template_id must be unique.'),
    ]

    @api.model
    def create_productview(self, vals, test=False):
        # returns True if the operation in the db was successful, False otherwise
        res_partner_id = vals.get('res_partner_id')
        product_template_id = vals.get('product_template_id')
        last_product_id = vals.get('last_product_id')
        view_date = vals.get('view_date')
        if not view_date:
            view_date = fields.Datetime.now()

        with self.pool.cursor() as pv_cr:
            if test:
                pv_cr = self._cr
            pv_cr.execute('''
                UPDATE product_view SET last_product_id=%s, write_date=%s WHERE res_partner_id=%s AND product_template_id=%s AND write_date < %s RETURNING id;
                ''', (last_product_id, view_date, res_partner_id, product_template_id, view_date))
            fetch = pv_cr.fetchone()
            if fetch:
                return True
            else:
                # update failed
                try:
                    with tools.mute_logger('odoo.sql_db'):
                        pv_cr.execute('''
                            INSERT INTO product_view (res_partner_id, product_template_id, last_product_id, write_date)
                            SELECT %s,%s,%s,%s
                            RETURNING id;
                            ''', (res_partner_id, product_template_id, last_product_id, view_date))
                    fetch = pv_cr.fetchone()
                    if fetch:
                        return True
                except IntegrityError:
                    return False
