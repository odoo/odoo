/** @odoo-module */
import { SaleOrderManagementScreen } from "@pos_sale/js/OrderManagementScreen/SaleOrderManagementScreen";
import { useListener } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const { useState } = owl;

export class MobileSaleOrderManagementScreen extends SaleOrderManagementScreen {
    static template = "MobileSaleOrderManagementScreen";
    setup() {
        super.setup();
        useListener("click-order", this._onShowDetails);
        this.mobileState = useState({ showDetails: false });
    }
    _onShowDetails() {
        this.mobileState.showDetails = true;
    }
}

registry.category("pos_screens").add("MobileSaleOrderManagementScreen", MobileSaleOrderManagementScreen);
