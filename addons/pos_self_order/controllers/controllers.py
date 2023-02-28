# -*- coding: utf-8 -*-
import logging
import werkzeug
import uuid
from odoo import fields, http, _
from odoo.http import request
from odoo.osv.expression import AND
from odoo.tools import format_amount

import json

from itertools import groupby

class PosSelfOrder(http.Controller):
    """
    This is the controller for the POS Self Order App
    """
    # test route
    @http.route('/pos-self-order/test', auth='public', website=True)
    def pos_self_order_test(self, pos_id=None):

        products_sudo = request.env['product.template'].sudo().search(
            [('available_in_pos', '=', True),
             ('name', '=', 'Desk Organizer'),
            ],
            )
        print(products_sudo.read(['attribute_line_ids', 'name']))
        print(products_sudo.read(['attribute_line_ids'])[0].get('attribute_line_ids'))
        products_sudo2 = request.env['product.product'].sudo().search(
            [('available_in_pos', '=', True),
             ('name', '=', 'Desk Organizer'),
            ],
            )
        print(products_sudo2.read(['attribute_line_ids', 'name']))
        print(products_sudo2.read(['attribute_line_ids'])[0].get('attribute_line_ids'))

        # print(products_sudo.read())
        #         , 'sale_ok': True, 'purchase_ok': True, 'uom_id': (1, 'Units'), 'uom_name': 'Units', 'uom_po_id': (1, 'Units'), 'company_id': False, 'seller_ids':
        #  [], 'variant_seller_ids': [], 'color': 0, 'attribute_line_ids': [4, 5], 'valid_product_template_attribute_line_ids': [4, 5], 'product_variant_ids': [42], 'product_variant_id': (42, '[FURN_0001] Desk Organizer'), 'product_vari
        # ant_count': 1, 'has_configurable_attributes': True, 'product_tooltip': 'Storable products are physical items for which you manage the inventory level.', 'priority': '0', 'product_tag_ids': [], 'taxes_id': [], 'supplier_taxes_i
        # d': [2], 'property_account_income_id': (20, '400000 Product Sales'), 'property_account_expense_id': (26, '600000 Expenses'), 'account_tag_ids': [], 'fiscal_country_codes': 'US', 'responsible_id': (1, 'OdooBot'), 'property_stoc
        # k_production': (15, 'Virtual Locations/Production'), 'property_stock_inventory': (14, 'Virtual Locations/Inventory adjustment'), 'sale_delay': 0.0, 'tracking': 'none', 'description_picking': False, 'description_pickingout': Fa
        # lse, 'description_pickingin': False, 'location_id': False, 'warehouse_id': False, 'has_available_route_ids': False, 'route_ids': [], 'route_from_categ_ids': [], 'available_in_pos': True, 'to_weight': True, 'pos_categ_id': (1,
        # 'Miscellaneous')}]
        # pos_session_sudo = getPosSessionSudo(pos_id)

        # domain = [
        #     ('state', 'in', ['opening_control', 'opened']),
        #     ('rescue', '=', False),
        #     ('config_id', '=', int(pos_id)),
        # ]
        # pos_session_sudo = request.env['pos.session'].sudo().search(
        #     domain, limit=1).read(['id', 'name'])
        # print("atts:", pos_session_sudo._get_attributes_by_ptal_id())
        # return json.dumps(get_attributes_by_ptal_id(), indent=4, sort_keys=True, default=str)
        return "Hello World"

    @http.route('/pos-self-order/', auth='public', website=True)
    def pos_self_order_start(self, table_id=None, pos_id=None, message_to_display=None):
        """
        The user gets this route from the QR code that they scan at the table
        This START ROUTE will render the LANDING PAGE of the POS Self Order App
        And it will pass some generic variabiles to the template: pos_id, table_id, pos_name, currency

        We get some details about this POS from the model "pos.config"

        If the POS is not open, we display a message to the user, saying the restaurant is closed
        the user will still be able to see the menu and even add items to the cart,
        but they will not be able to send the order
        """
        # TODO: we should have another parameter: personal_access_token
        # if self_order_location == 'table', this access token will be
        # the access token of that table from the restaurant.table model
        # (at the moment, there is no access token for this model, but we can either add it
        # or we can use some hash based on the fields of this model)
        # this access token will be written in the url of the QR code
        # ---------------
        # if self_order_location == 'kiosk', this access_token could be different
        # for each session. This could also be a hash based on the fields of the
        # pos.session model. This means that each time the restaurant employee
        # wants to open the kiosk, they will have to get the latest link from the
        # backend. This way, the kioks becomes much more secure, even though the
        # route will still be public.
        # This means that if self_order_location == 'kiosk', it would be virtually impossible
        # for someone else to send an order to the POS, because they would need to know
        # the access token of the current session.

        # TODO: maybe add a new route where the user can choose the pos_id
        # and then redirect to this route with the pos_id ( i don't think we need this for now )
        if not pos_id:
            raise werkzeug.exceptions.NotFound()
        # FIXME: check if table_id and pos_id exist
        # if not, send the user to the generic page where they can choose the POS and the table
        pos_sudo = request.env['pos.config'].sudo().search(
            [('id', '=', pos_id)])

        if not pos_sudo.self_order_allow_view_menu():
            raise werkzeug.exceptions.NotFound()

        if not pos_sudo.has_active_session:
            message_to_display = "restaurant_is_closed"

        # On the landing page of the app we can have a number of custom links
        # they are defined by the restaurant employee in the backend
        custom_links_sudo = request.env['pos_self_order.custom_link'].sudo().search([
        ], order='sequence')
        custom_links_list = custom_links_sudo.filtered(lambda link: int(pos_id) in [
                                                       pos.id for pos in link.pos_config_id] or not link.pos_config_id).read(['name', 'url', 'style'])
        context = {
            'pos_id': pos_id,
            'pos_name': pos_sudo.name,
            'currency_id': pos_sudo.currency_id.id,
            'pos_categories': request.env['pos.category'].sudo().search([]).read(['name', 'parent_id', 'child_id']),
            'message_to_display': message_to_display,
            'self_order_allow_order': pos_sudo.self_order_allow_order(),
            'show_prices_with_tax_included': True,
            'self_order_location': pos_sudo.compute_self_order_location(),
            'allows_ongoing_orders': pos_sudo.self_order_allows_ongoing_orders(),
            'payment_methods': pos_sudo.payment_method_ids.read(['name']),
            'custom_links': custom_links_list,
            'attributes_by_ptal_id': get_attributes_by_ptal_id(),
        }
        if pos_sudo.module_pos_restaurant:
            context.update({
                'total_number_of_tables': len(pos_sudo.get_tables_order_count()),
                'table_id': 0 if len(pos_sudo.get_tables_order_count()) == 0 else table_id,
            })
        # TODO: make sure it is ok to send session_info to frontend
        session_info = request.env['ir.http'].session_info()
        session_info['pos_self_order'] = context
        response = request.render(
            'pos_self_order.pos_self_order_index', {
                'session_info': session_info,
            })
        return response

    @http.route('/pos-self-order/get-menu', auth='public', type="json", website=True)
    def pos_self_order_get_menu(self, pos_id=None):
        """
        This is the route that the POS Self Order App uses to GET THE MENU
        :param pos_id: the id of the POS
        :type pos_id: int

        :return: the menu
        :rtype: list of dict
        """
        if not pos_id:
            raise werkzeug.exceptions.NotFound()
        pos_sudo = request.env['pos.config'].sudo().search(
            [('id', '=', pos_id)])
        if not pos_sudo.self_order_allow_view_menu():
            raise werkzeug.exceptions.NotFound()
        # TODO: only get the products that are available in THIS POS
        products_sudo = request.env['product.product'].sudo().search(
            [('available_in_pos', '=', True)], order='pos_categ_id')

        # FIXME: we are not taking into account product variants
        # for each of the items in products_sudo, we get the price with tax included
        menu = [{
            **{
                'price_info': product.get_product_info_pos(product.list_price, 1, int(pos_id))['all_prices'],
                'attribute_line_ids': product.read(['attribute_line_ids'])[0].get('attribute_line_ids'),
            },
            **product.read(['id', 'name', 'description_sale', 'pos_categ_id'])[0],
        } for product in products_sudo]
        return menu

    # FIXME: crop the images to be square -- maybe we want to do this in the frontend?
    # TODO: maybe we want to lazy load the images
    # TODO: right now this route will return the image to whoever calls it; is there any reason to not make it public?
    @http.route('/pos-self-order/get-images/<int:product_id>', methods=['GET'], type='http', auth='public')
    def pos_self_order_get_images(self, product_id):
        """
        This is the route that the POS Self Order App uses to GET THE PRODUCT IMAGES

        :param product_id: the id of the product
        :type product_id: int

        """
        # We get the product with the specific id from the database
        product_sudo = request.env['product.product'].sudo().browse(product_id)
        # We return the image of the product in binary format
        # 'image_1920' is the name of the field that contains the image
        # If the product does not have an image, the function _get_image_stream_from will return the default image
        return request.env['ir.binary']._get_image_stream_from(product_sudo, field_name='image_1920').get_response()

    @http.route('/pos-self-order/send-order/<int:pos_id>/<int:table_id>/', auth='public', type="json", website=True)
    def pos_self_order_send_order(self, cart, pos_id, table_id=0, order_id=None, access_token=None):
        """
        This is the route that the POS Self Order App uses to SEND THE ORDER
        There are 3 types of self order pos configurations:
        1. Order from Kiosk 
                ==> pos_allows_ongoing_orders = False
        2. Order from personal device and pay after each order
                ==> pos_allows_ongoing_orders = False
        3. Order from personal device and pay at the end of the meal
                ==> pos_allows_ongoing_orders = True
        In cases 1. and 2., we will create a new order each time the user sends an order
        In case 3., we will create a new order only if the user does not have an ongoing order
            (we will look whether there is an order with state = 'draft'
            at the table that the user has provided through the table_id parameter)
            (if we find an ongoing order, we will only allow the user to add items to that 
            order if he has provided the correct order_id and access_token -- this order_id
            and access_token must match the order_id and access_token of the ongoing order )

        :param cart: the cart variable contains the order.         
        :type cart: list of dictionaries with keys: product_id, qty
        :param pos_id: the id of the POS where the order is being sent
        :type pos_id: int
        :param table_id: the id of the table where the order is being sent
        :type table_id: int
        :param order_id: the id of the order that is being edited
        :type order_id: str  -- ex: "Order 00001-001-0001" 
        :param access_token: the access token of the order that is being edited
        :type access_token: str  -- UUID v4
        :return: dictionary with keys: order_id, access_token, order_total, date, state, order_items

        """
        # TODO: we need to check if the order is valid --
        # We have to check the cart variable -- this is the variable that contains the order
        # we also have to check if the pos_id and table_id are valid
        # the values of cart have to be integers, for ex, etc.

        pos_sudo = request.env['pos.config'].sudo().search(
            [('id', '=', pos_id)])

        if not pos_sudo.self_order_allow_order():
            raise werkzeug.exceptions.NotFound()

        pos_session_sudo = getPosSessionSudo(pos_id)

        sequence_number = None
        existing_order_sudo = None
        # Here we determine whether to make a new order or to add items to an existing order
        if pos_sudo.self_order_allows_ongoing_orders() and order_id:
            existing_order_sudo = request.env['pos.order'].sudo().search(
                [('pos_reference', '=', order_id)], limit=1)
            if existing_order_sudo and existing_order_sudo.state == "draft":
                if access_token == existing_order_sudo["access_token"]:
                    sequence_number = existing_order_sudo["sequence_number"]
                    cart = returnCartUpdatedWithItemsFromExistingOrder(
                        cart, existing_order_sudo)
        # if the conditions above are not met, we will create a new order
        if not sequence_number:
            sequence_number = findNewSequenceNumber(
                pos_id, table_id, pos_session_sudo["id"])
            order_id = generate_unique_id(
                pos_session_sudo["id"], 900+table_id, sequence_number)

        lines = createOrderLinesFromCart(cart, pos_id)
        amount_total = computeAmountTotalFromOrderLines(lines)
        # TODO: there are some fields that are not set
        order = {'id': order_id,
                 'data':
                 {
                     'name': order_id,
                     'amount_paid': 0,
                     'amount_total': amount_total,
                     'amount_tax': computeAmountTaxFromOrderLines(lines),
                     'amount_return': 0,
                     'lines': lines,
                     'statement_ids': [],
                     'pos_session_id': pos_session_sudo.get("id"),
                     #  FIXME: find out what pricelist_id to use
                     #  'pricelist_id': 1,
                     'partner_id': False,
                     'user_id': request.session.uid,
                     # we only need the digits of the order_id, not the whole id, which starts with word "Order"
                     'uid': order_id[6:],
                     'sequence_number': sequence_number,
                     'creation_date': str(fields.Datetime.now()),
                     'fiscal_position_id': False,
                     'to_invoice': False,
                     'to_ship': False,
                     'is_tipped': False,
                     'tip_amount': 0,
                     #  If the order is new, we will generate a new access token
                     #  If the order is an update of an existing order, we will keep the same access token
                     'access_token': uuid.uuid4().hex if not (existing_order_sudo and existing_order_sudo.state == "draft") else existing_order_sudo.access_token,
                     'customer_count': 1,
                     #  FIXME: is server_id ever mandatory?
                     # maybe for restaurants and not for bars?
                     "server_id": False,
                     #  'multiprint_resume': '{}',
                     #  TODO: configure the printing_changes variable
                     #   'printing_changes': '{"new":[{"product_id":55,"name":"Bacon Burger","customer_note":"","quantity":1}],"cancelled":[]}',

                 },
                 'to_invoice': False,
                 'session_id': pos_session_sudo.get("id")}

        if table_id:
            order["data"].update(table_id=table_id)

        # FIXME: ERROR rd-dem odoo.addons.point_of_sale.models.pos_order:
        # Could not fully process the POS Order: Order / is not fully paid.
        # When i write an order i get this error.
        # When the regular pos writes an order (even if not paid, just draft state),
        # it does not get this error

        order_resp = request.env['pos.order'].sudo().create_from_ui([order])[0]
        # is_trusted is set to True by default.
        # We need to set it to False, because we are creating an order from a public route
        # FIXME: make it so we only set it to false if it is a new order
        # if the server already aknowledged the order, we should not set it to false again
        # every time the user adds a new item to the order
        request.env['pos.order'].sudo().browse(
            order_resp.get('id')).is_trusted = False
        order_id = order_resp.get("pos_reference")
        response = {
            "order_id": order['data']['name'],
            "order_items": [{"product_id": line[2]["product_id"], "qty": line[2]["qty"]} for line in order["data"]["lines"]],
            "order_total": order['data']['amount_total'],
            "date": order["data"]["creation_date"],
            "access_token": order["data"]["access_token"],
            "state": "draft",
            "amount_tax": order["data"]["amount_tax"],
        }
        return response

    @http.route('/pos-self-order/view-order', auth='public', type="json", website=True)
    def pos_self_order_view_order(self, order_id=None, access_token=None):
        """
        Return some information about a given order.
        This is used by the frontend to find the latest state of an order.
        (e.g. if a customer orders something from the self order app and then the waiter adds an item to the order,
        the customer will be able to see the new item in the order)

        :parmam order_id: the id of the order that we want to view
        :type order_id: str
        :param access_token: the access token of the order that we want to view -- this is needed 
                             for security reasons, so that only the customer who created the order
                             can view it
        :type access_token: str
        """
        if not order_id or not access_token:
            raise werkzeug.exceptions.NotFound()
        order_sudo = request.env['pos.order'].sudo().search(
            [('pos_reference', '=', order_id)], limit=1)
        if not order_sudo:
            raise werkzeug.exceptions.NotFound()
        order_sudo = order_sudo[0]
        if access_token != order_sudo.read(['access_token'])[0].get('access_token'):
            raise werkzeug.exceptions.NotFound()
        order_json = order_sudo.export_for_ui()[0]
        return {
            'order_id': order_id,
            'access_token': access_token,
            'state': order_sudo['state'],
            'date': str(order_json.get("creation_date")),
            'amount_total': order_sudo['amount_total'],
            'amount_tax': order_sudo['amount_tax'],
            'items': [
                {
                    'product_id': line[2]['product_id'],
                    'qty': line[2]['qty'],
                }
                for line in order_json['lines']
            ],
        }


def returnCartUpdatedWithItemsFromExistingOrder(cart, existing_order):
    """
    If the customer has an existing order, we will add the items from the existing order to the current cart.
    (This is because the create_from_ui method will overwrite the old items from the order)

    :param cart: The cart from the frontend.
    :type cart: list of objects with keys: product_id, qty, and (optionally) customer_note.
    :param existing_order: The existing order.
    :type existing_order: pos.order object

    :return: The cart with the items from the existing order.
    :rtype: list of objects with keys: product_id, qty, (optionally) uuid, and (optionally) customer_note.
    """
    # there are some fields from the old order that we want to keep: uuid
    # and, if we don't have a new customer_note, then we keep the old customer_note
    for line in existing_order.lines:
        # if there is a line with the same product, we will update the quantity of the product
        for item in cart:
            if item["product_id"] == line["product_id"].id:
                item["qty"] += line["qty"]
                item["uuid"] = line["uuid"]
                if not item.get("customer_note"):
                    item["customer_note"] = line["customer_note"]
                break
        # if there is no line with the same product, we will create a new line
        else:
            cart.append({
                "product_id": line["product_id"].id,
                "qty": line["qty"],
                'uuid': line["uuid"],
                'customer_note': line["customer_note"],
            })
    return cart


def createOrderLinesFromCart(cart, pos_id):
    """
    Function that constructs the order lines (as the create_from_ui method expects them) from the cart.

    From the frontend we only get the id of the product and the quantity.
    We need to get the other details of the product from the database.
    This is done for security reasons.

    :param cart: The cart from the frontend.
    :type cart: list of objects with keys: product_id, qty and (optionally) uuid, and (optionally) customer_note.
    :param pos_id: The id of the pos.
    :type pos_id: int.

    :returns: list 
    """
    lines = []
    for item in cart:
        product_sudo = request.env['product.product'].sudo().search(
            [('available_in_pos', '=', True), ('id', '=', item.get("product_id"))], limit=1)

        # TODO: add the rest of the fields
        lines.append([0, 0, {
            'product_id': item.get('product_id'),
            'qty': item.get('qty'),
            'price_extra': item.get('price_extra'),
            'price_unit': product_sudo.list_price,
            'price_subtotal': product_sudo.list_price * item.get('qty'),
            'price_subtotal_incl': product_sudo.get_product_info_pos(product_sudo.list_price, item.get('qty'), int(pos_id))['all_prices']['price_with_tax'] * item.get('qty'),
            'discount': 0,
            'tax_ids': product_sudo.taxes_id,
            'id': 1,
            'pack_lot_ids': [],
            'description': item.get('description'),
            'full_product_name': product_sudo.name,
            'price_extra': 0,
            'customer_note': item.get('customer_note'),
            'price_manually_set': False,
            'note': '',
            'uuid': uuid.uuid4().hex if not item.get("uuid") else item.get("uuid"),
        }])
    return lines


def computeAmountTotalFromOrderLines(lines):
    """
    Compute the amount total from the order lines.

    :param lines: The order lines.
    :type lines: List of 'pos.order.line' objects.

    :return: The amount total.
    :rtype: float.
    """
    return sum(orderline[2].get("price_subtotal_incl") for orderline in lines)


def computeAmountTaxFromOrderLines(lines):
    """
    Compute the total amount of tax from the order lines.

    :param lines: The order lines.
    :type lines: List of 'pos.order.line' objects.

    :return: The amount total.
    :rtype: float.
    """
    return sum(orderline[2].get("price_subtotal_incl")-orderline[2].get("price_subtotal") for orderline in lines)


def findNewSequenceNumber(pos_id, table_id, session_id):
    """
    Find the new sequence number for the order.

    :param pos_id: The id of the pos.
    :type pos_id: int.
    :param table_id: The id of the table.
    :type table_id: int.
    :param session_id: The id of the session.
    :type session_id: int.

    :return: The new sequence number.
    :rtype: int.
    """
    sequence_number = 1
    # TODO: TEST if this is correct
    old_sequence_number = request.env['pos.order'].sudo().search([('config_id', '=', int(pos_id)),
                                                                  ("pos_reference", "=like", f"Order {session_id:0>5}-{900 + table_id}-____")]).read(['sequence_number'])
    if old_sequence_number:
        old_sequence_number = old_sequence_number[0].get("sequence_number")
        sequence_number = old_sequence_number + 1
    return sequence_number


# the 2nd argument of order_id is the login number;
# the regular pos receives the login number from the backend on the first load
# the problem is that if the pos has login number 1, for example
# and we create a new order in the database, with sequence number 1, for example,
# when the regular pos will try to create a new order, it will also use sequence number 1
# and login number 1 and the new order will have the same id as the order created by the self order app
# so it will ultimately not be recorded in the database.
# ( the regular pos does not check what was the last order id from the database )
# it keeps track itself of the last order id -- this is why this problem occurs
# I thought that it is best to make the pos_self_order app work around
# the problem, instead of modifying the regular pos.
# so I decided to use the numbers from 900 to 999 for the login number
# this way, the regular pos will  have a login number of 1, 2, 3, etc
# and the pos_self_order app will have a login number of 901, 902, 903, etc,
# where 901 is the login number of the table with id = 1,
# 902 is the login number of the table with id = 2, etc
# TODO: make it so the regular pos can't have a login number of 900 or more
def generate_unique_id(id, login_number, sequence_number):
    """
    This function resembles the one with the same name in the models.js file.
    Generates a public identification number for the order.
    ex: f"{id:0>5}" will return a string with 5 digits => if the id is 1, the result will be 00001
    """
    return f"Order {id:0>5}-{login_number:0>3}-{sequence_number:0>4}"


def getPosSessionSudo(pos_id):
    """
    Get the object of the last open session of the pos with the given id.

    :param pos_id: The id of the pos.
    :type pos_id: int.

    :returns: object
    """
    domain = [
        ('state', 'in', ['opening_control', 'opened']),
        ('rescue', '=', False),
        ('config_id', '=', int(pos_id)),
    ]
    pos_session_sudo = request.env['pos.session'].sudo().search(
        domain, limit=1).read(['id', 'name'])
    # if the restaurant is not open, we send an error message to the client
    if not pos_session_sudo:
        # FIXME: this error is not working
        raise werkzeug.exceptions.NotFound()
    return pos_session_sudo[0]
def get_attributes_by_ptal_id():
        product_attributes = request.env['product.attribute'].sudo().search([('create_variant', '=', 'no_variant')])
        product_attributes_by_id = {product_attribute.id: product_attribute for product_attribute in product_attributes}
        domain = [('attribute_id', 'in', product_attributes.mapped('id'))]
        product_template_attribute_values = request.env['product.template.attribute.value'].sudo().search(domain)
        # print("product_template_attribute_values:", json.dumps(product_template_attribute_values.read(), indent=4, sort_keys=True, default=str))
        # vlad = request.env['product.template.attribute.value'].sudo().browse(17)
        # print("vlad:", vlad.read(['price_extra']))
        key = lambda ptav: (ptav.attribute_line_id.id, ptav.attribute_id.id)
        res = {}
        for key, group in groupby(sorted(product_template_attribute_values, key=key), key=key):
            attribute_line_id, attribute_id = key
            values = [{**ptav.product_attribute_value_id.read(['name', 'is_custom', 'html_color'])[0],
                       'price_extra': ptav.price_extra} for ptav in list(group)]
            res[attribute_line_id] = {
                'id': attribute_line_id,
                'name': product_attributes_by_id[attribute_id].name,
                'display_type': product_attributes_by_id[attribute_id].display_type,
                'values': values
            }
        # print("res: ", json.dumps(res, indent=4, sort_keys=True, default=str))
        return res