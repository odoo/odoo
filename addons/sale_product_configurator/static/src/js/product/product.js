/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import {
    ProductTemplateAttributeLine as PTAL
} from "../product_template_attribute_line/product_template_attribute_line";

export class Product extends Component {
    static components = { PTAL };
    static template = "sale_product_configurator.product";
    static props = {
        id: { type: [Number, {value: false}], optional: true },
        product_tmpl_id: Number,
        display_name: String,
        description_sale: [Boolean, String], // backend sends 'false' when there is no description
        price: Number,
        quantity: Number,
        attribute_lines: Object,
        optional: Boolean,
        imageURL: { type: String, optional: true },
        archived_combinations: Array,
        exclusions: Object,
        parent_exclusions: Object,
        parent_product_tmpl_ids: { type: Array, element: Number, optional: true },
    };

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Increase the quantity of the product in the state.
     */
    increaseQuantity() {
        this.env.setQuantity(this.props.product_tmpl_id, this.props.quantity+1);
    }

    /**
     * Set the quantity of the product in the state.
     *
     * @param {Event} event
     */
    setQuantity(event) {
        this.env.setQuantity(this.props.product_tmpl_id, parseFloat(event.target.value));
    }

    /**
     * Decrease the quantity of the product in the state.
     */
    decreaseQuantity() {
        this.env.setQuantity(this.props.product_tmpl_id, this.props.quantity-1);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the price, in the format of the given currency.
     *
     * @return {String} - The price, in the format of the given currency.
     */
    getFormattedPrice() {
        return formatCurrency(this.props.price, this.env.currencyId);
    }
}
