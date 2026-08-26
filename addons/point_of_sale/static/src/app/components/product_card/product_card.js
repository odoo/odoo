import { Component, useProps, t } from "@odoo/owl";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { formatFloat } from "@web/core/utils/numbers";

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    props = useProps({
        class: t.string().optional(""),
        name: t.string(),
        available: t.boolean().optional(true),
        product: t.or([t.instanceOf(ProductTemplate), t.instanceOf(ProductProduct)]),
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
        const productUnit = this.props.product.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit"
        );
        return formatFloat(this.props.productCartQty ?? 0, {
            digits: [true, productUnit.digits],
            trailingZeros: false,
        });
    }
}
