# -*- coding: utf-8 -*-
import logging
import werkzeug
import uuid
from odoo import fields, http, _
from odoo.http import request
from odoo.osv.expression import AND
from odoo.tools import format_amount


class PosSelfOrder(http.Controller):
    """
    This is the controller for the POS Self Order App
    """
    # test route
    @http.route('/pos-self-order/test', auth='public', website=True)
    def pos_self_order_test(self, pos_id=None):
        # we get the custom links that we want to show for this POS
        pos_sudo = request.env['pos.config'].sudo().browse(int(pos_id))
        print("pos_sudo", pos_sudo.self_order_kiosk_mode)
        print("pos_sudo", pos_sudo.self_order_phone_mode)
        print("pos_sudo", pos_sudo.compute_self_order_location())
        print("pos_sudo open tabs ", pos_sudo.self_order_pay_after)

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
        pos_sudo = request.env['pos.config'].sudo().search([('id', '=', pos_id)])

        if not pos_sudo.self_order_allow_view_menu():   
            raise werkzeug.exceptions.NotFound()

        if not pos_sudo.has_active_session:
            message_to_display = "restaurant_is_closed"

        # On the landing page of the app we can have a number of custom links
        # they are defined by the restaurant employee in the backend
        custom_links_sudo = request.env['pos_self_order.custom_link'].sudo().search([])
        # TODO: i'm not sure that it's intuitive to have the custom links show in the app when the pos_config_id is empty
        custom_links_list = custom_links_sudo.filtered(lambda link: int(pos_id) in [pos.id for pos in link.pos_config_id] or not link.pos_config_id).read(['name', 'url'])
        context = {
            'pos_id': pos_id,
            'pos_name': pos_sudo.name,
            'currency_id': pos_sudo.currency_id.id,
            'pos_categories': request.env['pos.category'].sudo().search([]).read(['name', 'parent_id', 'child_id']),
            'message_to_display': message_to_display,
            'self_order_allow_order': pos_sudo.has_active_session and pos_sudo.self_order_allow_order(),
            'show_prices_with_tax_included': True,
            'self_order_location': pos_sudo.compute_self_order_location(),
            'allow_open_tabs': pos_sudo.self_order_allow_open_tabs(),
            'payment_methods' : pos_sudo.payment_method_ids.read(['name']),
            'custom_links' : custom_links_list,
        }
        if pos_sudo.module_pos_restaurant:
            context.update({
                'total_number_of_tables': len(pos_sudo.get_tables_order_count()),
                'table_id': 0 if len(pos_sudo.get_tables_order_count()) == 0 else table_id,
            })
        
        response = request.render(
            'pos_self_order.pos_self_order_index', context)
        return response


    # this is the route that the POS Self Order App uses to GET THE MENU
    @http.route('/pos-self-order/get-menu', auth='public', type="json", website=True)
    def pos_self_order_get_menu(self, pos_id=None):
        if not pos_id:
            raise werkzeug.exceptions.NotFound() 
        pos_sudo = request.env['pos.config'].sudo().search([('id', '=', pos_id)])
        if not pos_sudo.self_order_allow_view_menu():   
            raise werkzeug.exceptions.NotFound()
        # TODO: only get the products that are available in THIS POS
        products_sudo = request.env['product.product'].sudo().search(
            [('available_in_pos', '=', True)])
        # for each of the items in products_sudo, we get the price with tax included
        menu = list(map(lambda product:
        { 
            **{
                'price_info' : product.get_product_info_pos(product.list_price, 1, int(pos_id))['all_prices'],
            },  
                **product.read(['id', 'name', 'description_sale', 'pos_categ_id'])[0],
        }, products_sudo))
        return menu

    # FIXME: crop the images to be square -- maybe we want to do this in the frontend?
    # TODO: maybe we want to lazy load the images
    # TODO: right now this route will return the image to whoever calls it; is there any reason to not make it public?
    # this is the route that the POS Self Order App uses to GET THE PRODUCT IMAGES
    @http.route('/pos-self-order/get-images/<int:product_id>', methods=['GET'], type='http', auth='public')
    def pos_self_order_get_images(self, product_id):
        # We get the product with the specific id from the database
        product_sudo = request.env['product.product'].sudo().browse(product_id)
        # We return the image of the product in binary format
        # 'image_1920' is the name of the field that contains the image
        # If the product does not have an image, the function _get_image_stream_from will return the default image
        return request.env['ir.binary']._get_image_stream_from(product_sudo, field_name='image_1920').get_response()

    @http.route('/pos-self-order/send-order/<int:pos_id>/<int:table_id>/', auth='public', type="json", website=True)
    def pos_self_order_send_order(self, cart, pos_id, table_id=0, order_id=None, access_token=None ):
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


        pos_sudo = request.env['pos.config'].sudo().search([('id', '=', pos_id)])

        if not pos_sudo.self_order_allow_order():   
            raise werkzeug.exceptions.NotFound()

        pos_session_sudo = getPosSessionSudo(pos_id)

        sequence_number = None
        existing_order_sudo = None
        # Here we determine whether to make a new order or to add items to an existing order
        if order_id:
            existing_order_sudo = request.env['pos.order'].sudo().search(
                [('pos_reference', '=', order_id)], limit=1)
            if existing_order_sudo and existing_order_sudo.state == "draft":
                if access_token == existing_order_sudo["access_token"]:
                    sequence_number = existing_order_sudo["sequence_number"]
                    cart = returnCartUpdatedWithItemsFromExistingOrder(cart, existing_order_sudo)
        # if the conditions above are not met, we will create a new order
        if not sequence_number:
            sequence_number = findNewSequenceNumber(pos_id, table_id, pos_session_sudo["id"])
            order_id = generate_unique_id(pos_session_sudo["id"], 900+table_id, sequence_number)

        
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
                     'uid': order_id[6:], #  we only need the digits of the order_id, not the whole id, which starts with word "Order"
                     'sequence_number': sequence_number,
                     #  the date is formatted in the way that the regular POS does it
                     #  'creation_date': str(fields.Datetime.now()).replace(" ", "T"),
                     #  FIXME: there is a problem with the time
                     # when the regular pos creates an order, the time shown is correct
                     # when self order creates an order, the time shown is also correct
                     # but when the regular pos adds a new item to an existing order that
                     # was created with the self order, the time shown is 1 hour ahead
                     'creation_date': str(fields.Datetime.now()),
                     'fiscal_position_id': False,
                     'to_invoice': False,
                     'to_ship': False,
                     'is_tipped': False,
                     'tip_amount': 0,
                    #  If the order is new, we will generate a new access token
                    #  If the order is an update of an existing order, we will keep the same access token
                     'access_token': uuid.uuid4().hex if not (existing_order_sudo and existing_order_sudo.state=="draft") else existing_order_sudo.access_token,
                     'customer_count': 1,
                    #  FIXME: is server_id ever mandatory?
                    # maybe for restaurants and not for bars?
                     "server_id": False,
                     #  'multiprint_resume': '{}',
                     #  TODO: configure the printing_changes variable
                    #   'printing_changes': '{"new":[{"product_id":55,"name":"Bacon Burger","note":"","quantity":1}],"cancelled":[]}',

                 },
                 'to_invoice': False,
                 'session_id': pos_session_sudo.get("id")}

        if table_id:
            order["data"].update(table_id = table_id)
        
        # FIXME: ERROR rd-dem odoo.addons.point_of_sale.models.pos_order: 
        # Could not fully process the POS Order: Order / is not fully paid.  
        # When i write an order i get this error.
        # When the regular pos writes an order (even if not paid, just draft state),
        # it does not get this error


        order_sudo =  request.env['pos.order'].sudo().create_from_ui([order])[0]
        order_id = order_sudo.get("pos_reference")
        response_sudo = {
            "order_id": order_id,
            "order_items": [{"product_id": line[2]["product_id"], "qty": line[2]["qty"] } for line in order["data"]["lines"]],
            "order_total": amount_total, 
            "date": order["data"]["creation_date"],
            "access_token": order["data"]["access_token"],
            "state": "draft",
            "amount_tax": order["data"]["amount_tax"],
        }
        return response_sudo



    @http.route('/pos-self-order/view-order', auth='public', type="json" , website=True)
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
        order_sudo = request.env['pos.order'].sudo().search([('pos_reference' , '=', order_id)], limit=1)
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
            'date': str(order_json.get("creation_date")) ,
            'amount_total': order_sudo['amount_total'],
            'amount_tax': order_sudo['amount_tax'],
            'items': [
                    {
                        'product_id' : line[2]['product_id'],
                        'qty'        : line[2]['qty'],
                    } 
                    for line in order_json['lines']
            ],
        }

def returnCartUpdatedWithItemsFromExistingOrder(cart, existing_order):
    """
    If the customer has an existing order, we will add the items from the existing order to the cart.
    
    :param cart: The cart from the frontend.
    :type cart: list of objects with keys: product_id, qty
    :param existing_order: The existing order.
    :type existing_order: pos.order object

    :return: The cart with the items from the existing order.
    :rtype: list of objects with keys: product_id, qty and (optionally) uuid.
    """
    # if there is a line with the same product, we will update the quantity of the product
    # if there is no line with the same product, we will create a new line
    for line in existing_order.lines:
        for item in cart:
            if item["product_id"] == line["product_id"].id:
                item["qty"] += line["qty"]
                break
        else:
            cart.append({
                "product_id": line["product_id"].id,
                "qty": line["qty"],
                'uuid': line["uuid"],
            })
    return cart


def createOrderLinesFromCart(cart, pos_id):
    """
    From the frontend we only get the id of the product and the quantity.
    We need to get the other details of the product from the database.
    This is done for security reasons.

    :param cart: The cart from the frontend.
    :type cart: list of objects with keys: product_id, qty and (optionally) uuid.
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
            'price_unit': product_sudo.list_price,
            'price_subtotal': product_sudo.list_price * item.get('qty'),
            'price_subtotal_incl': product_sudo.get_product_info_pos(product_sudo.list_price, item.get('qty'), int(pos_id))['all_prices']['price_with_tax'],
            'discount': 0,
            'tax_ids': product_sudo.taxes_id,
            'id': 1,
            'pack_lot_ids': [],
            'description': '',
            'full_product_name': product_sudo.name,
            'price_extra': 0,
            'customer_note': '',
            'price_manually_set': False,
            'note': '',                                                                                                              
            'uuid': uuid.uuid4().hex if not item.get("uuid") else item.get("uuid"),
        }])
    return lines
def computeAmountTotalFromOrderLines(lines):
    return sum(orderline[2].get("price_subtotal_incl") for orderline in lines)
def computeAmountTaxFromOrderLines(lines):
    return sum(orderline[2].get("price_subtotal_incl")-orderline[2].get("price_subtotal") for orderline in lines)

def findNewSequenceNumber(pos_id, table_id, session_id):
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







