# -*- coding: utf-8 -*-

import json
from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError


class WooInstance(models.Model):
    _description = "Woo Instance"
    _name = 'woo.instance'

    name = fields.Char('Instance Name')
    client_id = fields.Char('Consumer Key')
    client_secret = fields.Char('Consumer Secret')

    url = fields.Char('Authorization URL')
    version = fields.Selection([('wc/v3', 'wc/V3')], 'Version')
    woo_company_id = fields.Many2one('res.company', string="Company")
    color = fields.Integer("Color Index")
    dashboard_graph_data = fields.Text(compute='_kanban_dashboard_graph')
    active = fields.Boolean('Active', default=True)

    def login(self):
        try:
            location = self.url
            cons_key = self.client_id
            sec_key = self.client_secret
            version = 'wc/v3'
            wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)
            r = wcapi.get("")
        except:
            raise UserError(
                _("Connection Unsuccessful..!! \nPlease check your Url,Consumer Key or Consumer Secret / Refresh Connection"))

        if r.status_code == 200:
            raise UserError(_("Congratulations, WooCommerce and Odoo connection has been successfully established"))
        else:
            raise UserError(
                _("Connection Unsuccessful..!! \nPlease check your Url,Consumer Key or Consumer Secret / Refresh Connection"))

    def _kanban_dashboard_graph(self):
        if not self._context.get('sort'):
            context = dict(self.env.context)
            context.update({'sort': 'week'})
            self.env.context = context

        for record in self:
            values = record.get_woo_dashboard_data(record)
            total_sales = round(sum([key['y'] for key in values]), 2)
            order_data = record.instance_total_orders()
            product_data = record.instance_products()
            customer_data = record.instance_customers()
            tax_data = record.instance_taxes()
            category_data = record.instance_product_categ()
            attribute_data = record.instance_product_attribute()
            record.dashboard_graph_data = json.dumps({
                "values": values,
                "title": "",
                "key": "Order: Untaxed amount",
                "area": True,
                "color": "#875A7B",
                "is_sample_data": False,
                "total_sales": total_sales,
                "order_data": order_data,
                "product_data": product_data,
                "customer_data": customer_data,
                "tax_data": tax_data,
                "category_data": category_data,
                "attribute_data": attribute_data,
                "sort_on": self._context.get('sort'),
                "currency_symbol": record.woo_company_id.currency_id.symbol or '',
            })

    def get_woo_dashboard_data(self, record):

        def graph_week_data(record):
            self._cr.execute("""SELECT to_char(date(d.day),'DAY'), t.amount_untaxed as sum
                                FROM  (
                                   SELECT day
                                   FROM generate_series(date(date_trunc('week', (current_date)))
                                    , date(date_trunc('week', (current_date)) + interval '6 days')
                                    , interval  '1 day') day
                                   ) d
                                LEFT   JOIN 
                                (SELECT date(date_order)::date AS day, sum(amount_untaxed) as amount_untaxed
                                   FROM   sale_order
                                   WHERE  date(date_order) >= (select date_trunc('week', date(current_date)))
                                   AND    date(date_order) <= (select date_trunc('week', date(current_date)) + interval '6 days')
                                   AND woo_instance_id=%s and state in ('sale','done')
                                   GROUP  BY 1
                                   ) t USING (day)
                                ORDER  BY day;""" % record.id)
            return self._cr.dictfetchall()

        def graph_year_data(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',month),'MONTH')),sum(amount_untaxed) from
                                    (
                                    SELECT 
                                      DATE_TRUNC('month',date(day)) as month,
                                      0 as amount_untaxed
                                    FROM generate_series(date(date_trunc('year', (current_date)))
                                        , date(date_trunc('year', (current_date)) + interval '1 YEAR - 1 day')
                                        , interval  '1 MONTH') day
                                    union all
                                    SELECT DATE_TRUNC('month',date(date_order)) as month,
                                    sum(amount_untaxed) as amount_untaxed
                                      FROM   sale_order
                                    WHERE  date(date_order) >= (select date_trunc('year', date(current_date))) AND date(date_order)::date <= (select date_trunc('year', date(current_date)) + '1 YEAR - 1 day')
                                    and woo_instance_id = %s and state in ('sale','done')
                                    group by DATE_TRUNC('month',date(date_order))
                                    order by month
                                    )foo 
                                    GROUP  BY foo.month
                                    order by foo.month""" % record.id)
            return self._cr.dictfetchall()

        def graph_month_data(record):
            self._cr.execute("""select EXTRACT(DAY from date(date_day)) :: integer,sum(amount_untaxed) from (
                        SELECT 
                          day::date as date_day,
                          0 as amount_untaxed
                        FROM generate_series(date(date_trunc('month', (current_date)))
                            , date(date_trunc('month', (current_date)) + interval '1 MONTH - 1 day')
                            , interval  '1 day') day
                        union all
                        SELECT date(date_order)::date AS date_day,
                        sum(amount_untaxed) as amount_untaxed
                          FROM   sale_order
                        WHERE  date(date_order) >= (select date_trunc('month', date(current_date)))
                        AND date(date_order)::date <= (select date_trunc('month', date(current_date)) + '1 MONTH - 1 day')
                        and woo_instance_id = %s and state in ('sale','done')
                        group by 1
                        )foo 
                        GROUP  BY 1
                        ORDER  BY 1""" % record.id)
            return self._cr.dictfetchall()

        def graph_all_data(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',date_order),'YYYY-MM')),sum(amount_untaxed)
                                from sale_order where woo_instance_id = %s and state in ('sale','done')
                                group by DATE_TRUNC('month',date_order) order by DATE_TRUNC('month',date_order)""" %
                             record.id)
            return self._cr.dictfetchall()

        if self._context.get('sort') == 'week':
            result = graph_week_data(record)
        elif self._context.get('sort') == "month":
            result = graph_month_data(record)
        elif self._context.get('sort') == "year":
            result = graph_year_data(record)
        else:
            result = graph_all_data(record)

        values = [{"x": ("{}".format(data.get(list(data.keys())[0]))), "y": data.get('sum') or 0.0} for data in result]
        return values

    def instance_total_orders(self):

        order_query = """select id from sale_order where woo_instance_id= %s and state in ('sale','done')""" % self.id

        def week_orders(order_query):
            qry = order_query + " and date(date_order) >= (select date_trunc('week', date(current_date))) order by date(date_order)"
            self._cr.execute(qry)

            return self._cr.dictfetchall()

        def month_orders(order_query):
            qry = order_query + " and date(date_order) >= (select date_trunc('month', date(current_date))) order by date(date_order)"
            self._cr.execute(qry)

            return self._cr.dictfetchall()

        def year_orders(order_query):
            qry = order_query + " and date(date_order) >= (select date_trunc('year', date(current_date))) order by date(date_order)"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def all_orders(record):
            self._cr.execute(
                """select id from sale_order where woo_instance_id = %s and state in ('sale','done')""" % record.id)

            return self._cr.dictfetchall()

        order_data = {}
        if self._context.get('sort') == "week":
            result = week_orders(order_query)
        elif self._context.get('sort') == "month":
            result = month_orders(order_query)
        elif self._context.get('sort') == "year":
            result = year_orders(order_query)
        else:
            result = all_orders(self)

        order_ids = [data.get('id') for data in result]
        view = self.env.ref('pragtech_woo_commerce.action_sale_order_woo').sudo().read()[0]
        action = self.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def prepare_action(self, view, domain):
        action = {
            'name': view.get('name'),
            'type': view.get('type'),
            'domain': domain,
            'view_mode': view.get('view_mode'),
            'view_id': view.get('view_id')[0] if view.get('view_id') else False,
            'views': view.get('views'),
            'res_model': view.get('res_model'),
            'target': view.get('target'),
        }

        if 'tree' in action['views'][0]:
            action['views'][0] = (action['view_id'], 'list')

        return action

    def instance_products(self):
        product_data = {}
        total_count = 0

        self._cr.execute(
            """select count(id) as total_count from product_template where is_exported = True and woo_instance_id = %s""" % self.id)
        result = self._cr.dictfetchall()

        if result:
            total_count = result[0].get('total_count')

        view = self.env.ref('sale.product_template_action').sudo().read()[0]
        action = self.prepare_action(view, [('is_exported', '=', True), ('woo_instance_id', '=', self.id)])
        product_data.update({
            'product_count': total_count,
            'product_action': action
        })

        return product_data

    def instance_customers(self):
        customer_data = {}
        self._cr.execute("""select id from res_partner where is_exported = True and woo_instance_id = %s""" % self.id)
        result = self._cr.dictfetchall()
        customer_ids = [data.get('partner_id') for data in result]
        view = self.env.ref('account.res_partner_action_customer').sudo().read()[0]
        action = self.prepare_action(view, [('is_exported', '=', True), ('woo_instance_id', '=', self.id)])
        customer_data.update({
            'customer_count': len(customer_ids),
            'customer_action': action
        })

        return customer_data

    def instance_taxes(self):
        tax_data = {}
        self._cr.execute("""select id from account_tax where is_exported = True and woo_instance_id = %s""" % self.id)
        result = self._cr.dictfetchall()
        tax_ids = [data.get('tax_id') for data in result]
        view = self.env.ref('account.action_tax_form').sudo().read()[0]
        action = self.prepare_action(view, [('is_exported', '=', True), ('woo_instance_id', '=', self.id)])
        tax_data.update({
            'tax_count': len(tax_ids),
            'tax_action': action
        })

        return tax_data

    def instance_product_categ(self):
        category_data = {}
        self._cr.execute(
            """select id from product_category where is_exported = True and woo_instance_id = %s""" % self.id)
        result = self._cr.dictfetchall()
        category_ids = [data.get('category_id') for data in result]
        view = self.env.ref('product.product_category_action_form').sudo().read()[0]
        action = self.prepare_action(view, [('is_exported', '=', True), ('woo_instance_id', '=', self.id)])
        category_data.update({
            'category_count': len(category_ids),
            'category_action': action
        })

        return category_data

    def instance_product_attribute(self):
        attribute_data = {}
        self._cr.execute(
            """select id from product_attribute where is_exported = True and woo_instance_id = %s""" % self.id)
        result = self._cr.dictfetchall()
        attribute_ids = [data.get('attribute_id') for data in result]
        view = self.env.ref('product.attribute_action').sudo().read()[0]
        action = self.prepare_action(view, [('is_exported', '=', True), ('woo_instance_id', '=', self.id)])
        attribute_data.update({
            'attribute_count': len(attribute_ids),
            'attribute_action': action
        })

        return attribute_data
