# -*- coding: utf-8 -*-

from typing import List, Dict, Optional, Union
import werkzeug
import uuid

from odoo import http, fields
from odoo.http import request

from odoo.addons.pos_self_order.controllers.utils import PosSelfOrderUtils
from odoo.addons.point_of_sale.models.product import ProductProduct
from odoo.addons.point_of_sale.models.pos_order import PosOrder
from odoo.addons.pos_self_order.models.pos_config import PosConfig


class PosSelfOrderController(http.Controller):
    @http.route(
        "/pos-self-order/send-order",
        auth="public",
        type="json",
        website=True,
    )
    def pos_self_order_send_order(
        self,
        cart: List[Dict],
        pos_config_id: int,
        table_access_token: Optional[str] = None,
        order_id: Optional[str] = None,
        order_access_token: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        There are 2 types of self order configurations:
        1. Order at table and pay after each order
                ==> pos_allows_ongoing_orders = False
        2. Order at table and pay at the end of the meal
                ==> pos_allows_ongoing_orders = True
        (order at table means order from personal device (smartphone))
        In case 1. we will create a new order each time the user sends an order
        In case 2. we will create a new order only if the user does not have an ongoing order
            (we will look whether there is an order with state = 'draft'
            with the same order_id and order_access_token as the ones that the user has provided)
        :param cart: the cart variable contains the order; list of dictionaries
        :param pos_config_id: the id of the POS where the order is being sent
        :param table_access_token: the access token of the table where the order is being sent (UUID v4)
        :param order_id: the id of the order that is being edited; ex: "Order 00001-001-0001"
        :param access_token: the access token of the order that is being edited (UUID v4)
        :return: dictionary with keys: pos_reference, access_token
        """
        # we will only respond with the order "access_token" and "id". After clicking on order, the customer will be redirected to the landing page,
        # from where the view order route will be automatically called anyways, so he will get the order details that way

        pos_config_sudo = PosSelfOrderUtils._get_pos_config_sudo(self, pos_config_id)

        if not pos_config_sudo.self_order_table_mode:
            raise werkzeug.exceptions.BadRequest()

        return (
            request.env["pos.order"]
            .sudo()
            .browse(
                int(
                    request.env["pos.order"]
                    .sudo()
                    .create_from_ui(
                        [
                            self._form_order(
                                self._create_order_data(
                                    cart,
                                    pos_config_sudo,
                                    table_access_token,
                                    order_id,
                                    order_access_token,
                                )
                            )
                        ],
                        draft=True,
                    )[0]
                    .get("id")
                )
            )
            .read(["pos_reference", "access_token"])[0]
        )

        # # is_trusted is set to True by default.
        # # We need to set it to False, because we are creating an order from a public route
        # # FIXME: make it so we only set it to false if it is a new order
        # # if the server already aknowledged the order, we should not set it to false again
        # # every time the user adds a new item to the order
        # request.env["pos.order"].sudo().browse(order_resp.get("id")).is_trusted = False

    # TODO: QUESTION: this function returns another function, which itself returns a dictionary. Is it ok to write the type hint of the return value of this
    # function as a dictionary?
    @http.route("/pos-self-order/view-order", auth="public", type="json", website=True)
    def pos_self_order_view_order(self, pos_reference: str, access_token: str) -> Dict:
        """
        Return some information about a given order.
        This is used by the frontend to find the latest state of an order.
        (e.g. if a customer orders something from the self order app and then the waiter adds an item to the order,
        the customer will be able to see the new item in the order)
        :parmam pos_reference: the id of the order that we want to view
        :param access_token: the access token of the order that we want to view -- this is needed
                             for security reasons, so that only the customer who created the order
                             can view it
        """
        order_sudo = self._find_order(pos_reference, access_token)
        if not order_sudo:
            raise werkzeug.exceptions.Unauthorized()
        return order_sudo._export_for_self_order()

    def _create_order_data(
        self,
        cart: List[Dict],
        pos_config_sudo: PosConfig,
        table_access_token: str,
        order_pos_reference: str,
        order_access_token: str,
    ) -> Dict[str, Union[int, str, List[Dict]]]:
        """
        Given the data, we decide whether we need to create a new order or update an existing one
        :return: dictionary with the data needed to create a new order
        """

        # We only care about the previous order if the customer is paying after the meal
        # ( paying after the meal means that the customer can order multiple times on the same order )
        order_sudo = pos_config_sudo.self_order_pay_after == "meal" and self._find_order(
            order_pos_reference, order_access_token, state="draft"
        )

        return {
            **(
                order_sudo
                and self._get_existing_order_data(order_sudo)
                or self._create_new_order_data(pos_config_sudo, table_access_token)
            ),
            "lines": self._create_orderlines(
                order_sudo and self._update_cart(cart, order_sudo.lines.export_for_ui()) or cart,
                pos_config_sudo,
            ),
        }

    def _get_existing_order_data(self, order_sudo: PosOrder) -> Dict[str, Union[str, int]]:
        """
        :param order_sudo: the order for which we want to get the data
        :return: a dictionary containing the fields from the order that interest us
        """
        return {
            "id": order_sudo.pos_reference,
            "sequence_number": order_sudo.sequence_number,
            "access_token": order_sudo.access_token,
            "session_id": order_sudo.session_id.id,
            "table_id": order_sudo.table_id.id,
        }

    def _create_new_order_data(
        self, pos_config_sudo: PosConfig, table_access_token: str
    ) -> Dict[str, Union[str, int]]:
        """
        :param pos_config_id: the id of the pos config for which we want to create the order
        :param table_access_token: the access token of the table for which we want to create the order
        :return: a dictionary containing the data that we need to create a new order
        """
        table_sudo = PosSelfOrderUtils._get_table_sudo(self, table_access_token)
        pos_session_sudo = pos_config_sudo.current_session_id
        if not table_sudo or not pos_session_sudo:
            raise werkzeug.exceptions.Unauthorized()

        sequence_number = self._get_sequence_number(table_sudo.id, pos_session_sudo.id)

        return {
            "id": self._generate_unique_id(pos_session_sudo.id, table_sudo.id, sequence_number),
            "sequence_number": sequence_number,
            "access_token": uuid.uuid4().hex,
            "session_id": pos_session_sudo.id,
            "table_id": table_sudo.id,
        }

    def _update_cart(
        self,
        cart: List[Dict],
        existing_orderlines: List[Dict],
    ) -> List[Dict]:
        """
        If the customer has an existing order, we will add the items from the existing order to the current cart.
        (This is because the create_from_ui method will overwrite the old items from the order)
        :param cart: The cart from the frontend.
        :return: list of dictionaries with the items from the cart and the items from the existing order
        """

        return self._get_updated_orderlines(
            existing_orderlines,
            [item for item in cart if self._is_in_cart(item, existing_orderlines)],
        ) + [item for item in cart if not self._is_in_cart(item, existing_orderlines)]

    def _get_updated_orderlines(self, orderlines: List[Dict], cart: List[Dict]) -> List[Dict]:
        """
        :returns updated version of orderlines that takes into account the new items from the cart
        """
        return [
            self._get_updated_orderline(line, updated_item)
            if (
                updated_item := next(
                    (item for item in cart if self._is_same_product(item, line)), None
                )
            )
            else line
            for line in orderlines
        ]

    def _get_updated_orderline(self, line: Dict, updated_item: Dict) -> Dict:
        """
        This function assumes that the price of the product was not changed between the time the
        first items were added to the order and the time the new items were added to the order.
        """
        qty_ratio = (updated_item["qty"] + line["qty"]) / line["qty"]
        return {
            **line,
            **{
                "price_subtotal": line["price_subtotal"] * qty_ratio,
                "price_subtotal_incl": line["price_subtotal_incl"] * qty_ratio,
                "qty": line["qty"] + updated_item["qty"],
                "customer_note": updated_item.get("customer_note") or line.get("customer_note"),
            },
        }

    def _is_in_cart(self, item: Dict, existing_orderlines: List[Dict]) -> bool:
        """
        :return: True if the item is in any of the orderlines, False otherwise
        """
        return any(self._is_same_product(item, line) for line in existing_orderlines)

    #  TODO: take into account "is_pos_groupable" field
    def _is_same_product(self, item, orderline):
        """
        :return: True if the item is the same product as the one in the orderline, False otherwise
        """
        return all(
            item.get(key) == orderline.get(key)
            for key in PosSelfOrderUtils._get_product_uniqueness_keys(self)
        )

    def _get_full_product_name(self, name: str, description: str) -> str:
        """
        :param name: ex: "[E-COM12] Desk Organizer"
        :param description: ex: "M, Leather"
        :return: ex: "Desk Organizer (M, Leather)"
        """
        return f"{name} ({description})" if description else name

    def _create_orderlines(self, cart: List[Dict], pos_config_sudo: PosConfig) -> List[Dict]:
        """
        Function that constructs the order lines (as the create_from_ui method expects them) from the cart.
        From the frontend we only get basic data of the cart, such as the id of the product and the quantity.
        We need to get the other details of the product from the database.
        This is done for security reasons.
        """

        return [
            [
                0,
                0,
                self._create_orderline(
                    item,
                    pos_config_sudo,
                ),
            ]
            # having the "full product name" means that the orderline is already in the db
            # so we don't need to create a new object
            if not item.get("full_product_name") else [0, 0, item]
            for item in cart
        ]

    def _create_orderline(self, item: Dict, pos_config_sudo: PosConfig) -> Dict:
        """
        Function that constructs an order line (as the create_from_ui method expects it) from an item from the cart.
        """
        product_sudo = request.env["product.product"].sudo().browse(int(item.get("product_id")))
        return {
            "product_id": item.get("product_id"),
            "qty": item.get("qty"),
            **self._get_orderline_price_info(product_sudo, item, pos_config_sudo),
            "discount": 0,
            "tax_ids": product_sudo.taxes_id,
            "pack_lot_ids": [],
            "description": item.get("description"),  # ex "M, Leather"
            "full_product_name": self._get_full_product_name(  # ex: "Desk Organizer (M, Leather)"
                product_sudo._get_name(),
                item.get("description"),
            ),
            "customer_note": item.get("customer_note"),
            "price_manually_set": False,
            "note": "",
            "uuid": str(uuid.uuid4()),
        }

    def _get_orderline_price_info(
        self, product_sudo: ProductProduct, item: Dict, pos_config_sudo: PosConfig
    ) -> Dict:
        """ """

        price_extra = (
            self._compute_price_extra(product_sudo, item.get("description"), pos_config_sudo)
            if item.get("description")
            else 0
        )
        price_unit = product_sudo.lst_price + price_extra
        price_subtotal_info = product_sudo._get_self_order_price(
            pos_config_sudo, price_unit, item.get("qty")
        )

        return {
            "price_unit": price_unit,
            "price_subtotal": price_subtotal_info["price_without_tax"],
            "price_subtotal_incl": price_subtotal_info["price_with_tax"],
            "price_extra": price_extra,
        }

    def _compute_price_extra(
        self, product_sudo: ProductProduct, description: str, pos_config_sudo: PosConfig
    ) -> float:
        """
        Function that computes the price_extra of a product based on the description.
        :param product_sudo: The product object.
        :param description: The description of the product.
        :return: The price_extra of the product.
        """

        return sum(
            v["price_extra"]["price_without_tax"]
            for attr, selected_value_name in zip(
                product_sudo._get_attributes(pos_config_sudo), description.split(", ")
            )
            for v in attr["values"]
            if v["name"] == selected_value_name
        )

    def _form_order(self, order: Dict) -> Dict:
        """
        Function that constructs an order object (as the create_from_ui method expects it)
        It takes as input the order object that was created by self._create_order_data()
        :param order: Dictionary representing an order.
        :return: Dictionary representing an order (as the create_from_ui method expects it).
        """
        # The self order can only update an order that was created on the self order itself.
        # This is because the self order does not have the ability to update orders that were created on the POS,
        # because the app wouldn't know the access token of the order.

        # TODO: there are some fields that are not set
        return {
            "id": order.get("id"),
            "data": {
                "name": order.get("id"),
                "amount_paid": 0,
                "amount_total": self._compute_amount_total(order.get("lines")),
                "amount_tax": self._compute_amount_tax(order.get("lines")),
                "amount_return": 0,
                "lines": order.get("lines"),
                "statement_ids": [],
                "pos_session_id": order.get("session_id"),
                #  FIXME: find out what pricelist_id to use
                #  'pricelist_id': 1,
                "partner_id": False,
                "user_id": request.session.uid,
                # we only need the digits of the order_id, not the whole id, which starts with word "Order"
                "uid": order.get("id")[6:],
                "sequence_number": order.get("sequence_number"),
                "creation_date": str(fields.Datetime.now()),
                "fiscal_position_id": False,
                "to_invoice": False,
                "to_ship": False,
                "is_tipped": False,
                "tip_amount": 0,
                "access_token": order.get("access_token"),
                "server_id": False,
                "table_id": order.get("table_id"),
            },
            "to_invoice": False,
            "session_id": order.get("session_id"),
        }

    def _compute_amount_total(self, lines: List[Dict]) -> float:
        return sum(orderline[2].get("price_subtotal_incl") for orderline in lines)

    def _compute_amount_tax(self, lines: List[Dict]) -> float:
        return sum(
            orderline[2].get("price_subtotal_incl") - orderline[2].get("price_subtotal")
            for orderline in lines
        )

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
    def _generate_unique_id(self, pos_session_id: int, table_id: int, sequence_number: int) -> str:
        """
        Generates a public identification number for the order.
        :return: The order name. Example: Order 00001-001-0001
        """
        return f"Order {pos_session_id:0>5}-{900 + table_id :0>3}-{sequence_number:0>4}"

    def _find_order(
        self, pos_reference: str, order_access_token: str, state: Optional[str] = None
    ) -> PosOrder:
        """
        :return: pos order with the given pos_reference, access token and state
        """
        return (
            pos_reference
            and order_access_token
            and request.env["pos.order"]
            .sudo()
            .search(
                [
                    ("pos_reference", "=", pos_reference),
                    ("access_token", "=", order_access_token),
                    *(state and [("state", "=", state)] or []),
                ],
                limit=1,
            )
        )

    def _get_sequence_number(self, table_id: int, session_id: int) -> int:
        """
        :return: the new sequence number for the order.
        """
        return (
            request.env["pos.order"]
            .sudo()
            .search(
                [
                    (
                        "pos_reference",
                        "=like",
                        f"Order {session_id:0>5}-{900 + table_id}-____",
                    ),
                ],
                limit=1,
            )
            .sequence_number
            + 1
        ) or 1
