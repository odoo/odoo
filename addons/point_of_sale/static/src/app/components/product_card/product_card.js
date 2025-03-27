import { Component } from "@odoo/owl";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    static props = {
        class: { String, optional: true },
        name: String,
        product: Object,
        productId: Number | String,
        comboExtraPrice: { String, optional: true },
        color: { type: [Number, undefined], optional: true },
        imageUrl: [String, Boolean],
        onClick: { type: Function, optional: true },
        showWarning: { type: Boolean, optional: true },
        productCartQty: { type: [Number, undefined], optional: true },
        slots: { type: Object, optional: true },
        isComboPopup: { type: Boolean, optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        class: "",
        showWarning: false,
        isComboPopup: false,
    };

    get productQty() {
        return this.env.utils.formatProductQty(this.props.productCartQty ?? 0, false);
    }
}
