
import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Product } from "../product/product";

export class ProductList extends Component {
    static components = { Product };
    static template = "sale.ProductList";
    props = useProps({
        products: t.array(),
        areProductsOptional: t.boolean().optional(false),
    });

    setup() {
        this.optionalProductsTitle = _t("Add optional products");
    }
}
