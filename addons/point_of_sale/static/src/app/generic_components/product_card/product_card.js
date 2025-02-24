import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

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
        productCartQty: { type: [Number, undefined], optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        onProductInfoClick: () => {},
        class: "",
        showWarning: false,
    };

    setup() {
        this.pos = usePos();
        this.qty_precision = this.pos.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit of Measure"
        ).digits;
    }
}
