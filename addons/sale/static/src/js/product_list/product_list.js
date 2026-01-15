
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Product } from "../product/product";

export class ProductList extends Component {
    static components = { Product };
    static template = "sale.ProductList";
    static props = {
        products: Array,
        areProductsOptional: { type: Boolean, optional: true },
    };
    static defaultProps = {
        areProductsOptional: false,
    };

    setup() {
        this.optionalProductsTitle = _t("Add optional products");
    }
}
