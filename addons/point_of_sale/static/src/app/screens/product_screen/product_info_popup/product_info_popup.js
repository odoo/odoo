/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";

export class ProductInfoPopup extends Component {
    static template = "point_of_sale.ProductInfoPopup";
    static components = { Dialog };
    static props = ["info", "product", "close"];

    setup() {
        this.pos = usePos();
    }
    searchProduct(productName) {
        this.pos.selectedCategoryId = 0;
        this.pos.searchProductWord = productName + ";product_tmpl_id:" + this.props.product.product_tmpl_id;;
        this.props.close();
    }
    _hasMarginsCostsAccessRights() {
        const isAccessibleToEveryUser =
            this.pos.config.is_margins_costs_accessible_to_every_user;
        const isCashierManager = this.pos.get_cashier().raw.role === "manager";
        return isAccessibleToEveryUser || isCashierManager;
    }
}
