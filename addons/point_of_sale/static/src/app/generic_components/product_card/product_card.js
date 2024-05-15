import { Component } from "@odoo/owl";
import { BlurryFillImage } from "@point_of_sale/app/generic_components/blurry_fill_image/blurry_fill_image";

export class ProductCard extends Component {
    static components = { BlurryFillImage };
    static template = "point_of_sale.ProductCard";
    static props = {
        class: { String, optional: true },
        name: String,
        productId: Number,
        price: String,
        color: { type: [Number, undefined], optional: true },
        imageUrl: [String, Boolean],
        productInfo: { Boolean, optional: true },
        onClick: { type: Function, optional: true },
        onProductInfoClick: { type: Function, optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        onProductInfoClick: () => {},
        class: "",
    };
}
