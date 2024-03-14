/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import {
    ProductTemplateAttributeLine as PTAL
} from "../product_template_attribute_line/product_template_attribute_line";

export class Product extends Component {
    static components = { PTAL };
    static template = "sale.Product";
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
        parent_product_tmpl_id: { type: Number, optional: true },
        price_info: { type: String, optional: true },
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
    async setQuantity(event) {
        const quantity = parseFloat(event.target.value);
        const didUpdateQuantity = await this.env.setQuantity(
            this.props.product_tmpl_id, isNaN(quantity) ? 0 : quantity
        );
        // If the quantity wasn't updated, the component won't rerender, and the input will display
        // a stale value. As a result, we need to manually rerender the input.
        if (!didUpdateQuantity) {
            this.render();
        }
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
        return formatCurrency(this.props.price, this.env.currency.id);
    }

    /**
     * Check whether this product is the main product.
     *
     * @return {Boolean} - Whether this product is the main product.
     */
    get isMainProduct() {
        return this.env.mainProductTmplId === this.props.product_tmpl_id;
    }
}
