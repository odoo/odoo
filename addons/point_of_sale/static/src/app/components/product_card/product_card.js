import { Component, props, types } from "@odoo/owl";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    props = props(
        {
            "class?": types.string(),
            name: types.string(),
            "available?": types.boolean(),
            product: types.object(),
            productId: types.or([types.number(), types.string()]),
            "comboExtraPrice?": types.string(),
            "color?": types.or([types.number(), types.literal(undefined)]),
            imageUrl: types.or([types.string(), types.boolean()]),
            "onClick?": types.function(),
            "showWarning?": types.boolean(),
            "productCartQty?": types.or([types.number(), types.literal(undefined)]),
            "slots?": types.object(),
            "isComboPopup?": types.boolean(),
        },
        {
            onClick: () => {},
            class: "",
            showWarning: false,
            isComboPopup: false,
            available: true,
        }
    );

    get productQty() {
        return this.env.utils.formatProductQty(this.props.productCartQty ?? 0, false);
    }
}
