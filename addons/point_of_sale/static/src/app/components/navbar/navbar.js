import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { isDisplayStandalone, isMobileOS } from "@web/core/browser/feature_detection";

import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { ProxyStatus } from "@point_of_sale/app/components/navbar/proxy_status/proxy_status";
import { SyncPopup } from "@point_of_sale/app/components/popups/sync_popup/sync_popup";
import {
    SaleDetailsButton,
    handleSaleDetails,
} from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { Component, onMounted, useState, useExternalListener } from "@odoo/owl";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { deduceUrl } from "@point_of_sale/utils";
import { user } from "@web/core/user";
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { PresetSlotsPopup } from "@point_of_sale/app/components/popups/preset_slots_popup/preset_slots_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

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
        this.state = useState({ searchBarOpen: false });
        this.debug = useService("debug");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.dialog = useService("dialog");
        this.isDisplayStandalone = isDisplayStandalone();
        this.isBarcodeScannerSupported = isBarcodeScannerSupported;
        onMounted(async () => {
            this.isSystemUser = await user.hasGroup("base.group_system");
        });
        useExternalListener(document, "keydown", this.handleKeydown.bind(this));
    }

    handleKeydown(event) {
        if (
            !this.ui.isSmall &&
            this.inputRef?.el &&
            document.activeElement !== this.inputRef.el &&
            !this.pos.getOrder()?.getSelectedOrderline() &&
            this.noOpenDialogs() &&
            event.key.length == 1
        ) {
            this.inputRef.el.focus();
            this.inputRef.el.value = event.key;
            event.preventDefault();
        }
    }

    noOpenDialogs() {
        return document.querySelectorAll(".modal-dialog, .debug-widget").length === 0;
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
        return this.pos.getOpenOrders().filter((order) => !order.table_id);
    }

    get appUrl() {
        return `/scoped_app?app_id=point_of_sale&app_name=${encodeURIComponent(
            this.pos.config.display_name
        )}&path=${encodeURIComponent(`pos/ui?config_id=${this.pos.config.id}`)}`;
    }

    async reloadProducts() {
        this.dialog.add(SyncPopup, {
            title: _t("Reload Products"),
            confirm: (fullReload) => this.pos.reloadData(fullReload),
        });
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

    get shouldDisplayPresetTime() {
        return this.pos.getOrder()?.preset_id?.use_timing;
    }

    async showSaleDetails() {
        await handleSaleDetails(this.pos, this.hardwareProxy, this.dialog);
    }

    async openPresetTiming() {
        const order = this.pos.getOrder();
        const data = await makeAwaitable(this.dialog, PresetSlotsPopup);

        if (data) {
            if (order.preset_id.id != data.presetId) {
                await this.pos.selectPreset(this.pos.models["pos.preset"].get(data.presetId));
            }

            order.preset_time = data.slot.sql_datetime;
            if (data.slot.datetime > DateTime.now()) {
                this.pos.addPendingOrder([order.id]);
                await this.pos.syncAllOrders();
            }
        }
    }

    get mainButton() {
        const screens = ["ProductScreen", "PaymentScreen", "ReceiptScreen", "TipScreen"];
        return screens.includes(this.pos.mainScreen.component.name) ? "register" : "order";
    }
}
