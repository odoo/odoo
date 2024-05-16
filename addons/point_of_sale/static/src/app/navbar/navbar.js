import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { ProxyStatus } from "@point_of_sale/app/navbar/proxy_status/proxy_status";
import { SaleDetailsButton } from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { SyncNotification } from "@point_of_sale/app/navbar/sync_notification/sync_notification";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { BackButton } from "@point_of_sale/app/navbar/back_button/back_button";
import { Component, useState } from "@odoo/owl";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { isBarcodeScannerSupported } from "@web/webclient/barcode/barcode_scanner";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { deduceUrl } from "@point_of_sale/utils";
import { View } from "@web/views/view";

export class Navbar extends Component {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        ProxyStatus,
        SaleDetailsButton,
        SyncNotification,
        BackButton,
        Input,
        Dropdown,
        DropdownItem,
        View,
    };
    static props = {};
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.debug = useService("debug");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.isBarcodeScannerSupported = isBarcodeScannerSupported;
    }
    onClickScan() {
        if (!this.pos.scanning) {
            this.pos.showScreen("ProductScreen");
            this.pos.mobile_pane = "right";
        }
        this.pos.scanning = !this.pos.scanning;
    }
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control && this.pos.session._has_cash_move_perm);
    }
    onCashMoveButtonClick() {
        this.hardwareProxy.openCashbox(_t("Cash in / out"));
        this.dialog.add(CashMovePopup);
    }
    async onTicketButtonClick() {
        if (this.isTicketScreenShown) {
            this.pos.closeScreen();
        } else {
            if (this._shouldLoadOrders()) {
                try {
                    this.pos.setLoadingOrderState(true);
                    const orders = await this.pos.getServerOrders();
                    if (orders && orders.length > 0) {
                        const message = _t(
                            "%s orders have been loaded from the server. ",
                            orders.length
                        );
                        this.notification.add(message);
                    }
                } finally {
                    this.pos.setLoadingOrderState(false);
                    this.pos.showScreen("TicketScreen");
                }
            } else {
                this.pos.showScreen("TicketScreen");
            }
        }
    }

    _shouldLoadOrders() {
        return this.pos.config.raw.trusted_config_ids.length > 0;
    }

    get isTicketScreenShown() {
        return this.pos.mainScreen.component === TicketScreen;
    }

    get orderCount() {
        return this.pos.get_order_list().length;
    }

    async closeSession() {
        const info = await this.pos.getClosePosInfo();
        await this.pos.data.resetIndexedDB();

        if (info) {
            this.dialog.add(ClosePosPopup, info);
        }
    }

    showBackButton() {
        return this.pos.showBackButton();
    }
    showBackButtonMobile() {
        return this.pos.showBackButton() && this.ui.isSmall && !this.pos.scanning;
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
            fetch(`${deduceUrl(this.pos.config.proxy_ip)}/hw_proxy/customer_facing_display`, {
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
}
