/** @odoo-module */
import { SaleOrderManagementScreen } from "@pos_sale/js/OrderManagementScreen/SaleOrderManagementScreen";
import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";

export class MobileSaleOrderManagementScreen extends SaleOrderManagementScreen {
    static template = "MobileSaleOrderManagementScreen";
    setup() {
        super.setup();
        this.mobileState = useState({ showDetails: false });
    }
    async onClickSaleOrder() {
        await this.super();
        this.mobileState.showDetails = true;
    }
}

registry.category("pos_screens").add("MobileSaleOrderManagementScreen", MobileSaleOrderManagementScreen);
