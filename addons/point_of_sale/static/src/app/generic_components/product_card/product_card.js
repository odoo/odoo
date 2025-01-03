import { Component } from "@odoo/owl";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    static props = {
        class: { String, optional: true },
        name: String,
        product: Object,
        productId: Number | String,
        price: String,
        color: { type: [Number, undefined], optional: true },
        imageUrl: [String, Boolean],
        productInfo: { Boolean, optional: true },
        onClick: { type: Function, optional: true },
        onProductInfoClick: { type: Function, optional: true },
        showWarning: { type: Boolean, optional: true },
        imageFitMode: { type: String, optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        onProductInfoClick: () => {},
        class: "",
        showWarning: false,
        imageFitMode: "contain",
    };
}
