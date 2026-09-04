import logging
from datetime import datetime

from odoo import fields, models

_logging = logging.getLogger("===+++=== eCom Sale Order ===+++===")


class EgSaleOrder(models.Model):
    _inherit = 'eg.sale.order'

    created_via = fields.Char(string="Created Via")
    woo_version = fields.Char(string="WC Version")
    status = fields.Selection(
        [('pending', 'Pending'), ("processing", "Processing"), ("on-hold", "On-Hold"), ("cancelled", "Cancelled"),
         ("refunded", "Refunded"), ("failed", "Failed"), ("trash", "Trash"), ("completed", "Completed")])

    currency = fields.Char(string="Currency")

    discount_total = fields.Float(string="Total Discount")
    discount_tax = fields.Float(string="Discount Tax")
    shipping_total = fields.Float(string="Shipping Total")
    shipping_tax = fields.Float(string="Shipping Tax")
    cart_tax = fields.Float(string="Cart Tax")
    total = fields.Float(string="Total")
    total_tax = fields.Float(string="Total Tax")
    prices_include_tax = fields.Boolean(string="Price Include with Tax")

    customer_id = fields.Many2one(comodel_name='eg.res.partner', string='Customer')
    customer_ip_address = fields.Char(string="Customer IP Address")
    customer_user_agent = fields.Char(string="Customer User Agent")
    customer_note = fields.Text(string="Customer Note")

    payment_method_title = fields.Char(string="Payment Title")
    transaction_id = fields.Integer(string="Transaction ID")

    date_paid = fields.Char(string="Payment Paid Date")
    date_completed = fields.Char(string="Order Completed date")
    cart_hash = fields.Char(string="Cart Hash")

    def woo_update_order_state(self, state=None):
        """
        In this method update order status to woocommerce.
        :param state: Wocommerce order state
        :return: Nothing
        """
        woo_api = self.instance_id
        try:  # TODO New Change
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        if not state:
            order_state = self.env['order.state.line'].search(
                [('odoo_order_state', '=', self.odoo_order_id.state)], limit=1)
            if order_state:
                state = order_state.woo_order_state
            else:
                return {"warning": {"message": (
                    "{}".format(self.odoo_order_id.state))}}
        if state:
            data = {'status': state, }
            woo_order_response = wcapi.put("orders/{}".format(self.inst_order_id), data).json()
            _logging.info("order state change to a {}".format(woo_order_response.get('status')))

    def import_woo_sale_order(self, instance_id=None, cron=None):
        """
        In this create sale order with product, customer, tax, add discount  and payment gateway when import sale order.
        :param instance_id: Browseable object of instance
        :param cron: yes or no
        :return: Nothing
        """
        if cron == "yes":  # New Changes by akash
            instance_ids = self.env["eg.ecom.instance"].search([('provider', '=', 'eg_woocommerce')])
        else:
            instance_ids = [instance_id]
        for instance_id in instance_ids:
            woo_api = instance_id
            page = 1
            while page > 0:
                status = "no"  # New Changes by akash
                text = ""
                partial = False
                history_id_list = []
                line_partial_list = []
                try:  # New Changes by akash
                    wcapi = woo_api.get_wcapi_connection()
                    if cron == "yes" and woo_api.last_order_date:
                        sale_order_response = wcapi.get(
                            'orders', params={'per_page': 100, 'page': page, 'after': woo_api.last_order_date})
                    else:
                        sale_order_response = wcapi.get('orders', params={'per_page': 100, 'page': page})
                except Exception as e:
                    return {"warning": {"message": (
                        "{}".format(e))}}
                if sale_order_response.status_code != 200:
                    return {"warning": {"message": (
                        "{}".format(sale_order_response.text))}}
                sale_order_response = sale_order_response.json()
                page += 1
                if not sale_order_response:
                    page = 0
                if cron == "yes" and sale_order_response:  # New Changes by akash
                    last_date_order = datetime.strptime(sale_order_response[0].get("date_created"), "%Y-%m-%dT%H:%M:%S")
                    woo_api.write({"last_order_date": last_date_order})
                for woo_sale_order_dict in sale_order_response:
                    line_partial = False
                    sale_order_id = None
                    status = "no"
                    text = ""
                    if woo_sale_order_dict.get('status') in ['pending', 'processing', 'on-hold', 'completed']:
                        eg_sale_order_id = self.search(
                            [('inst_order_id', '=', str(woo_sale_order_dict.get("id"))),
                             ('instance_id', '=', woo_api.id)])
                        odoo_order_id = self.env['sale.order'].search(
                            [('name', '=', woo_sale_order_dict.get("number"))])

                        if eg_sale_order_id and odoo_order_id:
                            _logging.info("{} order is a already created!!!".format(woo_sale_order_dict.get('number')))
                            status = "yes"
                            continue  # New Change
                        else:
                            if not odoo_order_id:
                                if woo_sale_order_dict.get("customer_id") != 0:
                                    customer_list = self.env['eg.res.partner'].import_customer(instance_id=instance_id,
                                                                                               woo_customer_dict=woo_sale_order_dict)
                                    #  New Changes by akash
                                    if customer_list:  # New Changes by akash
                                        odoo_order_id = self.env['sale.order'].create({
                                            'partner_id': customer_list[0].id,
                                            'partner_invoice_id': customer_list[1].id,
                                            'partner_shipping_id': customer_list[2].id,
                                            'name': woo_sale_order_dict.get('number'),
                                            'instance_id': woo_api.id,
                                        })
                                        product_list = []
                                        for line_item in woo_sale_order_dict.get('line_items'):
                                            eg_product_tmpl_id = self.env['eg.product.template'].search(
                                                [('inst_product_tmpl_id', '=', str(line_item.get('product_id')))])
                                            if not eg_product_tmpl_id:
                                                self.env['eg.product.template'].import_product_template(
                                                    instance_id=instance_id,
                                                    product_tmpl_dict=line_item)

                                            # Create a Tax Rate
                                            icpSudo = self.env['ir.config_parameter'].sudo()
                                            create_tax_rate = icpSudo.get_param(
                                                'eg_new_woocommerce_integration.create_tax_rate', default=True)
                                            tax_rate = icpSudo.get_param('eg_new_woocommerce_integration.tax_rate',
                                                                         default='woocommerce_tax')
                                            woo_tax_rate_list = []
                                            if create_tax_rate and tax_rate == 'woocommerce_tax':
                                                for woo_tax_dict in line_item.get('taxes'):
                                                    woo_tax_rate_id = self.env["woo.tax.rate"].search(
                                                        [('instance_id', '=', woo_api.id),
                                                         ("woo_tax_rate_id", "=", woo_tax_dict.get("id"))])
                                                    if not woo_tax_rate_id:
                                                        woo_tax_rate_id = self.env[
                                                            "woo.tax.rate"].import_woo_tax_rate(
                                                            woo_tax_id=woo_tax_dict.get("id"), instance_id=woo_api)
                                                    woo_tax_rate_list.append(woo_tax_rate_id.odoo_tax_rate_id.id)

                                            sale_order_line_obj = self.env['sale.order.line']
                                            if line_item.get('variation_id'):
                                                eg_product_id = self.env['eg.product.product'].search(
                                                    [('inst_product_id', '=', str(line_item.get('variation_id'))),
                                                     ('instance_id', '=', woo_api.id)])
                                            else:
                                                eg_product_id = self.env['eg.product.product'].search(
                                                    [('eg_tmpl_id.inst_product_tmpl_id', '=',
                                                      str(line_item.get('product_id'))),
                                                     ('instance_id', '=', woo_api.id)])
                                            if eg_product_id and eg_product_id.odoo_product_id:  # New Changes by akash
                                                odoo_sale_order_line_id = self.env['sale.order.line'].new({
                                                    'order_id': odoo_order_id.id,
                                                    'product_id': eg_product_id.odoo_product_id.id,
                                                    'product_uom': eg_product_id.odoo_product_id.uom_id.id,
                                                    'name': str(eg_product_id.odoo_product_id.name),
                                                    'product_uom_qty': line_item.get('quantity'),
                                                })
                                                odoo_sale_order_line_id._onchange_product_id_warning()
                                                odoo_sale_order_line_id._onchange_product_packaging_id()
                                                odoo_sale_order_line_id.price_unit = line_item.get('price')
                                                odoo_sale_order_line_id.product_uom_qty = line_item.get('quantity')
                                                odoo_sale_order_line_id.tax_id = woo_tax_rate_list
                                                order_line_values = odoo_sale_order_line_id._convert_to_write(
                                                    odoo_sale_order_line_id._cache)
                                                sale_order_line_obj.create(order_line_values)

                                                if woo_sale_order_dict.get('coupon_lines'):
                                                    sale_order_line_obj = self.env['sale.order.line']
                                                    for coupon_line_dict in woo_sale_order_dict.get('coupon_lines'):
                                                        coupon_product_id = self.env['product.product'].search(
                                                            [('name', '=', coupon_line_dict.get('code'))])
                                                        if coupon_product_id:
                                                            coupon_product_id = coupon_product_id
                                                        else:
                                                            coupon_product_id = self.env['product.product'].create(
                                                                {'name': coupon_line_dict.get('code')
                                                                 })
                                                        odoo_sale_order_line_id = self.env['sale.order.line'].new({
                                                            'order_id': odoo_order_id.id,
                                                            'product_id': woo_api.eg_discount_product_id.odoo_product_id.id,
                                                            'product_uom': coupon_product_id.uom_id.id,
                                                        })
                                                        odoo_sale_order_line_id.product_id_change()
                                                        odoo_sale_order_line_id.product_uom_change()
                                                        odoo_sale_order_line_id.name = "{} coupon apply and {} discount apply".format(
                                                            coupon_line_dict.get('code'),
                                                            coupon_line_dict.get('discount'))
                                                        odoo_sale_order_line_id.price_unit = 0
                                                        odoo_sale_order_line_id.product_uom_qty = 1
                                                        order_line_values = odoo_sale_order_line_id._convert_to_write(
                                                            odoo_sale_order_line_id._cache)
                                                        sale_order_line_obj.create(order_line_values)
                                                status = "yes"
                                                sale_order_id = odoo_order_id
                                            else:
                                                product_list.append(line_item.get("name"))
                                                text = "This Sale order is create but this products {} is not mapping so not add in sale order line".format(
                                                    product_list)
                                                sale_order_id = odoo_order_id
                                                line_partial = True
                                                line_partial_list.append(line_partial)
                                    else:
                                        text = "This sale order {} is not create because customer is not mapping".format(
                                            woo_sale_order_dict.get("number"))
                                        partial = True
                                        status = "no"
                                        _logging.info("Don't create order because don't find customer: {}".format(
                                            woo_sale_order_dict.get("number")))  # New Changes by akash
                                else:
                                    text = "This Sale order {} is not create because customer is guest".format(
                                        woo_sale_order_dict.get("number"))
                                    partial = True
                                    _logging.info("This Sale order {} is not create because customer is guest")

                            if not eg_sale_order_id and odoo_order_id:  # New Changes by akash
                                if odoo_order_id.order_line:
                                    payment_gateway_id = self.env['eg.account.journal'].search(
                                        [(
                                            'instance_payment_gateway_id', '=',
                                            woo_sale_order_dict.get("payment_method")),
                                            ('instance_id', '=', woo_api.id)])
                                    self.create([{
                                        'instance_id': woo_api.id,
                                        'inst_order_id': str(woo_sale_order_dict.get("id")),
                                        'odoo_order_id': odoo_order_id.id,
                                        'created_via': woo_sale_order_dict.get("created_via"),
                                        'woo_version': woo_sale_order_dict.get("version"),
                                        'status': woo_sale_order_dict.get("status"),

                                        'currency': woo_sale_order_dict.get("currency"),

                                        'discount_total': woo_sale_order_dict.get("discount_total"),
                                        'discount_tax': woo_sale_order_dict.get("discount_tax"),
                                        'shipping_total': woo_sale_order_dict.get("shipping_total"),
                                        'shipping_tax': woo_sale_order_dict.get("shipping_tax"),
                                        'cart_tax': woo_sale_order_dict.get("cart_tax"),
                                        'total': woo_sale_order_dict.get("total"),
                                        'total_tax': woo_sale_order_dict.get("total_tax"),
                                        'prices_include_tax': woo_sale_order_dict.get("prices_include_tax"),

                                        'eg_account_journal_id': payment_gateway_id.id,
                                        'payment_method_title': woo_sale_order_dict.get("payment_method_title"),
                                        'transaction_id': woo_sale_order_dict.get("transaction_id"),

                                        'date_paid': woo_sale_order_dict.get("date_paid"),
                                        'date_completed': woo_sale_order_dict.get("date_completed"),
                                    }])
                                    status = "yes"
                                    sale_order_id = odoo_order_id
                                else:
                                    text = "This Sale Order is not mapped because order have not order line"
                                    status = "no"
                                    sale_order_id = None
                                    odoo_order_id.unlink()
                    else:
                        _logging.info(
                            "{} order in {} state so not created in odoo".format(woo_sale_order_dict.get('number'),
                                                                                 woo_sale_order_dict.get('status')))
                        text = "{} order in {} state so not created in odoo".format(woo_sale_order_dict.get('number'),
                                                                                    woo_sale_order_dict.get('status'))
                        partial = True
                    if line_partial:
                        status = "partial"
                    elif not line_partial and status == "yes":
                        text = "This order is created"
                    eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                        "status": status,
                                                                        "process_on": "order",
                                                                        "process": "a",
                                                                        "instance_id": woo_api.id,
                                                                        "order_id": sale_order_id and sale_order_id.id or None,
                                                                        "child_id": True})
                    history_id_list.append(eg_history_id.id)
                partial_value = True
                if partial or partial_value in line_partial_list:
                    text = "Some order was created and some order is not create"
                    status = "partial"
                if status == "yes" and not partial and partial_value not in line_partial_list:
                    text = "All Order was successfully created"
                if not history_id_list:  # TODO New Change
                    status = "yes"
                    text = "All order was already mapped"
                eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                    "status": status,
                                                                    "process_on": "order",
                                                                    "process": "a",
                                                                    "instance_id": instance_id and instance_id.id or None,
                                                                    "parent_id": True,
                                                                    "eg_history_ids": [(6, 0, history_id_list)]})
