/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { usePos } from "@point_of_sale/app/pos_hook";

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
        this.pos = usePos();
        Object.assign(this, this.props.info);
    }
    searchProduct(productName) {
        this.pos.globalState.setSelectedCategoryId(0);
        this.pos.globalState.searchProductWord = productName;
        this.cancel();
    }
    _hasMarginsCostsAccessRights() {
        const isAccessibleToEveryUser =
            this.pos.globalState.config.is_margins_costs_accessible_to_every_user;
        const isCashierManager = this.pos.globalState.get_cashier().role === "manager";
        return isAccessibleToEveryUser || isCashierManager;
    }
}
