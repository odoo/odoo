# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, models, _


class ReportPricelist(models.AbstractModel):
    _name = 'report.product.report_pricelist'

    def _get_titles(self, form):
        titles = []
        for i in range(1, 6):
            field_name = 'qty%s' % str(i)
            title = _('%s units') % str(form[field_name])
            if form[field_name] != 0 and title not in titles:
                titles.append(title)
        return titles

    def _set_quantity(self, form):
        self.quantity = []
        for i in range(1, 6):
            field_name = 'qty%d' % i
            if form[field_name] > 0 and form[field_name] not in self.quantity:
                self.quantity.append(form[field_name])
            else:
                self.quantity.append(0)

    def _get_categories(self, products):
        res = []
        product_category = set(map((lambda p: (p.categ_id.id, p.categ_id.display_name)), products))
        for category_id, category_name in product_category:
            product = products.filtered(lambda p: p.categ_id.id == category_id)
            product_list = self._get_variants(product)
            res.append({'name': category_name, 'products': product_list})
        return res

    def _get_variants(self, products):
        res = []
        for product in products:
            val = {
                'name': product.name,
                'code': product.code,
                'attribute': ', '.join([attr.name for attr in product.attribute_value_ids])
            }
            for c, qty in enumerate(self.quantity, start=1):
                field_name = 'qty%s' % str(c)
                if qty > 0:
                    price_dict = self.pricelist.price_get(product.id, qty)
                    if price_dict[self.pricelist.id]:
                        price = price_dict[self.pricelist.id]
                    else:
                        price = product.list_price
                    val[field_name] = price
            res.append(val)
        return res

    @api.multi
    def render_html(self, data):
        Report = self.env['report']
        form = data.get('form')
        self.model = self.env.context.get('active_model')
        self._set_quantity(form)
        self.pricelist = self.env['product.pricelist'].browse(form['price_list'])
        selected_records = self.env[self.model].browse(data.get('ids'))
        docargs = {
            'doc_ids': data.get('ids'),
            'doc_model': self.model,
            'docs': selected_records,
            'time': time,
            'pricelist': self.pricelist.name,
            'currency': self.pricelist.currency_id.name,
            'titles': self._get_titles(form),
            'categories': self._get_categories(selected_records),
        }
        return Report.render('product.report_pricelist', docargs)
