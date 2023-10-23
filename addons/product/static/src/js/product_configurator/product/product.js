/** @odoo-module **/

import { Component } from "@odoo/owl";
import {
    ProductTemplateAttributeLine as PTAL
} from "../product_template_attribute_line/product_template_attribute_line";

export class Product extends Component {
    static components = { PTAL };
    static template = "product.product_configurator.product";
    static props = {
        id: { type: [Number, {value: false}] },
        product_tmpl_id: Number,
        display_name: String,
        description_sale: [String,  {value: false}],
        quantity: { type: Number, optional: true },
        attribute_lines: Object,
        imageURL: { type: String, optional: true },
        archived_combinations: Array,
        exclusions: Object,
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
}
