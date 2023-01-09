/** @odoo-module */
import SaleOrderManagementScreen from "@pos_sale/js/OrderManagementScreen/SaleOrderManagementScreen";
import Registries from "@point_of_sale/js/Registries";
import { useListener } from "@web/core/utils/hooks";

const { useState } = owl;

const MobileSaleOrderManagementScreen = (SaleOrderManagementScreen) => {
    class MobileSaleOrderManagementScreen extends SaleOrderManagementScreen {
        setup() {
            super.setup();
            useListener("click-order", this._onShowDetails);
            this.mobileState = useState({ showDetails: false });
        }
        _onShowDetails() {
            this.mobileState.showDetails = true;
        }
    }
    MobileSaleOrderManagementScreen.template = "MobileSaleOrderManagementScreen";
    return MobileSaleOrderManagementScreen;
};

Registries.Component.addByExtending(MobileSaleOrderManagementScreen, SaleOrderManagementScreen);

export default MobileSaleOrderManagementScreen;
