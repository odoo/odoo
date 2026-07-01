import { Component, props, t } from "@odoo/owl";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    props = props({
        class: t.string().optional(""),
        name: t.string(),
        available: t.boolean().optional(true),
        product: t.object(),
        productId: t.or([t.number(), t.string()]),
        comboExtraPrice: t.string().optional(),
        color: t.or([t.number(), t.literal(undefined)]).optional(),
        imageUrl: t.or([t.string(), t.boolean()]),
        onClick: t.function().optional(() => () => {}),
        showWarning: t.boolean().optional(false),
        productCartQty: t.or([t.number(), t.literal(undefined)]).optional(),
        isComboPopup: t.boolean().optional(false),
    });

    get productQty() {
        return this.env.utils.formatProductQty(this.props.productCartQty ?? 0, false);
    }
}
