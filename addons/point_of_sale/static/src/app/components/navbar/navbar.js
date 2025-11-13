import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";

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
import { barcodeService } from "@barcodes/barcode_service";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { user } from "@web/core/user";
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { _t } from "@web/core/l10n/translation";
import { uuidv4 } from "@point_of_sale/utils";
import { QrCodeCustomerDisplay } from "@point_of_sale/app/customer_display/customer_display_qr_code_popup";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";

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
        this.ui = useService("ui");
        this.state = useState({ searchBarOpen: false });
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.dialog = useService("dialog");
        this.isDisplayStandalone = isDisplayStandalone();
        this.isBarcodeScannerSupported = isBarcodeScannerSupported;
        this.timeout = null;
        this.bufferedInput = "";
        onMounted(async () => {
            this.isSystemUser = await user.hasGroup("base.group_system");
        });
        useExternalListener(document, "keydown", this.handleKeydown.bind(this));
        this.openPresetTiming = useAsyncLockedMethod(this.openPresetTiming);
    }

    handleKeydown(event) {
        const isEndCharacter = event.key?.match(/(Enter|Tab)/);
        const isSpecialKey =
            !["Control", "Alt"].includes(event.key) && (event.key?.length > 1 || event.metaKey);

        clearTimeout(this.timeout);
        if (isEndCharacter) {
            this.checkInput(event);
        } else {
            if (!isSpecialKey) {
                this.bufferedInput += event.key;
            }
            if (document.activeElement == this.inputRef?.el) {
                this.checkInput(event);
            } else {
                this.timeout = setTimeout(() => {
                    this.checkInput(event);
                }, barcodeService.maxTimeBetweenKeysInMs);
            }
        }
    }

    checkInput(event) {
        if (
            !this.ui.isSmall &&
            this.inputRef?.el &&
            document.activeElement !== this.inputRef.el &&
            !this.pos.getOrder()?.getSelectedOrderline() &&
            this.noOpenDialogs() &&
            event.key?.length == 1 &&
            this.bufferedInput.length < 3
        ) {
            this.inputRef.el.focus();
            this.inputRef.el.value = this.bufferedInput;
            event.preventDefault();
        }
        this.bufferedInput = "";
    }

    onClickRegister() {
        let order = this.pos.getOrder();

        if (!order) {
            order = this.pos.addNewOrder();
        }

        this.pos.navigateToOrderScreen(order);
    }

    noOpenDialogs() {
        return document.querySelectorAll(".modal-dialog, .debug-widget").length === 0;
    }
    onClickScan() {
        if (!this.pos.scanning) {
            const screenName = this.pos.router.state.current;
            if (["ProductScreen", "TicketScreen"].includes(screenName)) {
                const params =
                    screenName === "ProductScreen" ? { orderUuid: this.pos.getOrder().uuid } : {};
                this.pos.navigate(screenName, params);
            }
        }
        this.pos.ticket_screen_mobile_pane = this.pos.scanning ? "left" : "right";
        this.pos.mobile_pane = "right";
        this.pos.scanning = !this.pos.scanning;
    }
    get showCashMoveButton() {
        return this.pos.showCashMoveButton;
    }
    getOrderTabs() {
        return this.pos.getOpenOrders().filter((order) => !order.table_id);
    }

    get appUrl() {
        return `/scoped_app?app_id=point_of_sale&app_name=${encodeURIComponent(
            this.pos.config.display_name
        )}&path=${encodeURIComponent(`pos/ui/${this.pos.config.id}`)}`;
    }

    async reloadProducts() {
        this.dialog.add(SyncPopup, {
            title: _t("Reload Data"),
            confirm: (fullReload) => this.pos.reloadData(fullReload),
        });
    }

    openCustomerDisplay() {
        const getDeviceUuid = () => {
            if (!localStorage.getItem("device_uuid")) {
                localStorage.setItem("device_uuid", uuidv4());
            }
            return localStorage.getItem("device_uuid");
        };
        const customer_display_url = `/pos_customer_display/${
            this.pos.config.id
        }/${getDeviceUuid()}`;

        if (this.ui.isSmall) {
            this.dialog.add(QrCodeCustomerDisplay, {
                customerDisplayURL: `${this.pos.config._base_url}${customer_display_url}`,
            });
            return;
        }
        window.open(customer_display_url, "newWindow", "width=800,height=600,left=200,top=200");
        this.notification.add(_t("PoS Customer Display opened in a new window"));
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
        await this.pos.openPresetTiming();
    }

    get mainButton() {
        const screens = ["ProductScreen", "PaymentScreen", "ReceiptScreen", "TipScreen"];
        return screens.includes(this.pos.router.state.current) ? "register" : "order";
    }
}
