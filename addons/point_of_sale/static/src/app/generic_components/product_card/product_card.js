/** @odoo-module */

import { Component } from "@odoo/owl";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    static props = {
        class: { String, optional: true },
        name: String,
        productId: Number,
        price: String,
        imageUrl: String,
        productInfo: { Boolean, optional: true },
        onClick: { type: Function, optional: true },
        onProductInfoClick: { type: Function, optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        class: "",
    };
}
