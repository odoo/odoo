/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";

/**
 * Props:
 *  {
 *      info: {object of data}
 *  }
 */
export class ProductInfoPopup extends AbstractAwaitablePopup {
    static template = "ProductInfoPopup";
    static defaultProps = { confirmKey: false };

    setup() {
        super.setup();
        Object.assign(this, this.props.info);
    }
    searchProduct(productName) {
        this.env.posbus.trigger("search-product-from-info-popup", productName);
        this.cancel();
    }
    _hasMarginsCostsAccessRights() {
        const isAccessibleToEveryUser =
            this.env.pos.config.is_margins_costs_accessible_to_every_user;
        const isCashierManager = this.env.pos.get_cashier().role === "manager";
        return isAccessibleToEveryUser || isCashierManager;
    }
}
