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
<<<<<<< saas-17.2
        this.pos.setSelectedCategory(0);
        this.pos.searchProductWord = productName;
        this.props.close();
||||||| b64a507697381fd7bb205f4a2b2217322d31811a
        this.pos.setSelectedCategoryId(0);
        this.pos.searchProductWord = productName + ";product_tmpl_id:" + this.props.product.product_tmpl_id;
        this.cancel();
=======
        this.pos.setSelectedCategoryId(0);
        this.pos.searchProductWord = productName;
        this.cancel();
>>>>>>> 113bedef2cb2559412539c0a1ffb8f1f147e44ce
    }
    _hasMarginsCostsAccessRights() {
        const isAccessibleToEveryUser = this.pos.config.is_margins_costs_accessible_to_every_user;
        const isCashierManager = this.pos.get_cashier().raw.role === "manager";
        return isAccessibleToEveryUser || isCashierManager;
    }
}
