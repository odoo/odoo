import { Component } from "@odoo/owl";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    static props = {
        class: { type: String, optional: true },
        name: String,
        available: { type: Boolean, optional: true },
        product: Object,
        productId: [Number, String],
        comboExtraPrice: { type: String, optional: true },
        color: { type: [Number, { value: undefined }], optional: true },
        imageUrl: [String, Boolean],
        onClick: { type: Function, optional: true },
        showWarning: { type: Boolean, optional: true },
        productCartQty: { type: [Number, { value: undefined }], optional: true },
        slots: { type: Object, optional: true },
        isComboPopup: { type: Boolean, optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        class: "",
        showWarning: false,
        isComboPopup: false,
        available: true,
    };

    get productQty() {
        return this.env.utils.formatProductQty(this.props.productCartQty ?? 0, false);
    }
}
