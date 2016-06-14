# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.misc import formatLang


class ReportProductPricelist(models.AbstractModel):
    _name = 'report.product.report_pricelist'
    _template = 'product.report_pricelist'

    def _get_titles(self, form):
        lst = []
        vals = {}
        qtys = 1
        for i in range(1, 6):
            if form['qty'+str(i)] != 0:
                vals['qty'+str(qtys)] = str(form['qty'+str(i)]) + ' units'
            qtys += 1
        lst.append(vals)
        return lst

    def _set_quantity(self, form):
        for i in range(1, 6):
            q = 'qty%d' % i
            if form[q] > 0 and form[q] not in self.quantity:
                self.quantity.append(form[q])
            else:
                self.quantity.append(0)
        return True

    def _get_pricelist(self, pricelist_id):
        return self.env['product.pricelist'].browse(pricelist_id).name

    def _get_currency(self, pricelist_id):
        return self.env['product.pricelist'].browse(pricelist_id).currency_id.name

    def _get_categories(self, products, form):
        res = []
        self.pricelist = form['price_list']
        self._set_quantity(form)
        cats = products.mapped('categ_id').name_get()
        if not cats:
            return res
        for cat in cats:
            products_vals = []
            for product in products.filtered(lambda x: x.categ_id.id == cat[0]):
                val = {'id': product.id,
                        'name': product.name,
                        'code': product.code}
                i = 1
                for qty in self.quantity:
                    if qty == 0:
                        val['qty'+str(i)] = 0.0
                    else:
                        val['qty'+str(i)] = self._get_price(self.pricelist, product.id, qty)
                    i += 1
                products_vals.append(val)
            res.append({'name': cat[1], 'products': products_vals})
        return res

    def _get_price(self, pricelist_id, product_id, qty):
        sale_price_digits = self.env['decimal.precision'].precision_get('Product Price')
        pricelist = self.env['product.pricelist'].browse(pricelist_id)
        price_dict = pricelist.price_get(product_id, qty)
        if price_dict[pricelist.id]:
            price = formatLang(self.env, price_dict[pricelist.id], digits=sale_price_digits, currency_obj=pricelist.currency_id)
        else:
            list_price = self.env['product.product'].browse(product_id).list_price
            price = formatLang(self.env, list_price, digits=sale_price_digits, currency_obj=pricelist.currency_id)
        return price

    @api.multi
    def render_html(self, data=None):
        self.quantity = []
        data['form']['create_date'] = fields.Date.today()
        model = self.env.context.get('active_model')
        docargs = {
            'doc_ids': self.env.context.get('active_ids'),
            'doc_model': model,
            'objects': self.env[model].browse(self.env.context.get('active_ids')),
            'data': data['form'],
            'get_pricelist': self._get_pricelist,
            'get_currency': self._get_currency,
            'get_categories': self._get_categories,
            'get_price': self._get_price,
            'get_titles': self._get_titles,
        }
        return self.env['report'].render('product.report_pricelist', docargs)
