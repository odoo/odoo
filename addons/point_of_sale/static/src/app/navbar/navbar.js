import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { isDisplayStandalone, isMobileOS } from "@web/core/browser/feature_detection";

import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { ProxyStatus } from "@point_of_sale/app/navbar/proxy_status/proxy_status";
import { SyncPopup } from "@point_of_sale/app/components/popups/sync_popup/sync_popup";
import {
    SaleDetailsButton,
    handleSaleDetails,
} from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { Component, onMounted, useState } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { deduceUrl } from "@point_of_sale/utils";
import { user } from "@web/core/user";
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";

export class Navbar extends Component {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        ProxyStatus,
        SaleDetailsButton,
        Input,
        Dropdown,
        DropdownItem,
        SyncPopup,
        OrderTabs,
    };
    static props = {};
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.debug = useService("debug");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.isDisplayStandalone = isDisplayStandalone();
        this.isBarcodeScannerSupported = isBarcodeScannerSupported;
        onMounted(async () => {
            this.isSystemUser = await user.hasGroup("base.group_system");
        });
    }
    onClickScan() {
        if (!this.pos.scanning) {
            this.pos.showScreen("ProductScreen");
            this.pos.mobile_pane = "right";
        }
        this.pos.scanning = !this.pos.scanning;
    }
    get customerFacingDisplayButtonIsShown() {
        return this.pos.config.customer_display_type !== "none" && !isMobileOS();
    }
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control && this.pos.session._has_cash_move_perm);
    }
    getOrderTabs() {
        return this.pos.get_open_orders().filter((order) => !order.table_id);
    }

    get orderCount() {
        return this.pos.get_open_orders().length;
    }

    get appUrl() {
        return `/scoped_app?app_id=point_of_sale&app_name=${encodeURIComponent(
            this.pos.config.display_name
        )}&path=${encodeURIComponent(`pos/ui?config_id=${this.pos.config.id}`)}`;
    }

    toggleProductView() {
        const newView = this.pos.productListView === "grid" ? "list" : "grid";
        window.localStorage.setItem("productListView", newView);
        this.pos.productListView = this.pos.productListView === "grid" ? "list" : "grid";
    }

    get showToggleProductView() {
        return this.pos.mainScreen.component === ProductScreen && this.ui.isSmall;
    }
    openCustomerDisplay() {
        if (this.pos.config.customer_display_type === "local") {
            window.open(
                `/pos_customer_display/${this.pos.config.id}/${this.pos.config.access_token}`,
                "newWindow",
                "width=800,height=600,left=200,top=200"
            );
            this.notification.add("Connected");
        }
        if (this.pos.config.customer_display_type === "remote") {
            this.notification.add("Navigate to your POS Customer Display on the other computer");
        }
        if (this.pos.config.customer_display_type === "proxy") {
            this.notification.add("Connecting to the IoT Box");
            const proxyIP = this.pos.getDisplayDeviceIP();
            fetch(`${deduceUrl(proxyIP)}/hw_proxy/customer_facing_display`, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    params: {
                        action: "open",
                        access_token: this.pos.config.access_token,
                        pos_id: this.pos.config.id,
                    },
                }),
            })
                .then(() => {
                    this.notification.add("Connection successful", { type: "success" });
                })
                .catch(() => {
                    this.notification.add("Connection failed", { type: "danger" });
                });
        }
    }

    get showCreateProductButton() {
        return this.isSystemUser;
    }

    async showSaleDetails() {
        await handleSaleDetails(this.pos, this.hardwareProxy, this.dialog);
    }

    onSyncNotificationClick() {
        if (this.pos.data.network.offline) {
            this.pos.data.network.warningTriggered = false;
        }

        if (this.pos.data.network.unsyncData.length > 0) {
            this.dialog.add(SyncPopup, {
                confirm: () => this.pos.data.syncData(),
            });
        }
    }
}
