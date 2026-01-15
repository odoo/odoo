import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { isDisplayStandalone, isMobileOS } from "@web/core/browser/feature_detection";

import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { ProxyStatus } from "@point_of_sale/app/navbar/proxy_status/proxy_status";
import { SyncPopup } from "@point_of_sale/app/navbar/sync_popup/sync_popup";
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
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { openCustomerDisplay } from "@point_of_sale/customer_display/utils";
import { _t } from "@web/core/l10n/translation";

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
            this.hasProductCreationAccess = await this.pos.allowProductCreation();
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
    async clearCache() {
        await this.pos.data.resetIndexedDB();
        const items = { ...localStorage };
        for (const key in items) {
            localStorage.removeItem(key);
        }
        window.location.reload();
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
            this.notification.add(_t("PoS Customer Display opened in a new window"));
        }
        if (this.pos.config.customer_display_type === "remote") {
            this.notification.add(
                _t("Navigate to your PoS Customer Display on the other computer")
            );
        }
        openCustomerDisplay(
            this.pos.getDisplayDeviceIP(),
            this.pos.config.access_token,
            this.pos.config.id,
            this.notification
        );
    }

    get showCreateProductButton() {
        return this.hasProductCreationAccess;
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
