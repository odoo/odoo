/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, "pos_sale.Order", {
    //@override
    select_orderline(orderline) {
        this._super(...arguments);
        if (orderline && orderline.product.id === this.pos.config.down_payment_product_id[0]) {
            this.pos.numpadMode = "price";
        }
    },
    //@override
    _get_ignored_product_ids_total_discount() {
        const productIds = this._super(...arguments);
        productIds.push(this.pos.config.down_payment_product_id[0]);
        return productIds;
    },
});

patch(Orderline.prototype, "pos_sale.Orderline", {
    setup(_defaultObj, options) {
        this._super(...arguments);
        // It is possible that this orderline is initialized using `init_from_JSON`,
        // meaning, it is loaded from localStorage or from export_for_ui. This means
        // that some fields has already been assigned. Therefore, we only set the options
        // when the original value is falsy.
        this.sale_order_origin_id = this.sale_order_origin_id || options.sale_order_origin_id;
        this.sale_order_line_id = this.sale_order_line_id || options.sale_order_line_id;
        this.down_payment_details = this.down_payment_details || options.down_payment_details;
        this.customerNote = this.customerNote || options.customer_note;
        if (this.sale_order_origin_id && this.sale_order_origin_id.shipping_date) {
            this.order.setShippingDate(this.sale_order_origin_id.shipping_date);
        }
    },
    init_from_JSON(json) {
        this._super(...arguments);
        this.sale_order_origin_id = json.sale_order_origin_id;
        this.sale_order_line_id = json.sale_order_line_id;
        this.down_payment_details =
            json.down_payment_details && JSON.parse(json.down_payment_details);
    },
    export_as_JSON() {
        const json = this._super(...arguments);
        json.sale_order_origin_id = this.sale_order_origin_id;
        json.sale_order_line_id = this.sale_order_line_id;
        json.down_payment_details =
            this.down_payment_details && JSON.stringify(this.down_payment_details);
        return json;
    },
    get_sale_order() {
        if (this.sale_order_origin_id) {
            const value = {
                name: this.sale_order_origin_id.name,
                details: this.down_payment_details || false,
            };

            return value;
        }
        return false;
    },
    export_for_printing() {
        var json = this._super(...arguments);
        json.down_payment_details = this.down_payment_details;
        if (this.sale_order_origin_id) {
            json.so_reference = this.sale_order_origin_id.name;
        }
        return json;
    },
    /**
     * Set quantity based on the give sale order line.
     * @param {'sale.order.line'} saleOrderLine
     */
    setQuantityFromSOL(saleOrderLine) {
        if (this.product.type === "service") {
            this.set_quantity(saleOrderLine.qty_to_invoice);
        } else {
            this.set_quantity(
                saleOrderLine.product_uom_qty -
                    Math.max(saleOrderLine.qty_delivered, saleOrderLine.qty_invoiced)
            );
        }
    },
});
