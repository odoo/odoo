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
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { Component, onMounted, useState } from "@odoo/owl";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { isBarcodeScannerSupported } from "@web/webclient/barcode/barcode_scanner";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { deduceUrl } from "@point_of_sale/utils";
import { user } from "@web/core/user";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { ListContainer } from "@point_of_sale/app/generic_components/list_container/list_container";

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
        ListContainer,
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
    showTabs() {
        return true;
    }
    newFloatingOrder() {
        this.pos.add_new_order();
        this.pos.showScreen("ProductScreen");
    }
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
    }
    getFloatingOrders() {
        return this.pos.get_open_orders();
    }
    editOrderNote(order) {
        this.dialog.add(TextInputPopup, {
            title: _t("Edit order note"),
            placeholder: _t("Emma's Birthday Party"),
            startingValue: order.note || "",
            getPayload: async (newName) => {
                if (typeof order.id == "number") {
                    this.pos.data.write("pos.order", [order.id], {
                        note: newName,
                    });
                } else {
                    order.note = newName;
                }
            },
        });
    }
    onCashMoveButtonClick() {
        this.hardwareProxy.openCashbox(_t("Cash in / out"));
        this.dialog.add(CashMovePopup);
    }

    get orderCount() {
        return this.pos.get_open_orders().length;
    }

    get appUrl() {
        return `/scoped_app?app_id=point_of_sale&app_name=${encodeURIComponent(
            this.pos.config.display_name
        )}&path=${encodeURIComponent(`pos/ui?config_id=${this.pos.config.id}`)}`;
    }

    async closeSession() {
        const info = await this.pos.getClosePosInfo();
        await this.pos.data.resetIndexedDB();

        if (info) {
            this.dialog.add(ClosePosPopup, info);
        }
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
                    action: "open",
                    access_token: this.pos.config.access_token,
                    id: this.pos.config.id,
                }),
            })
                .then(() => {
                    this.notification.add("Connection successful");
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
