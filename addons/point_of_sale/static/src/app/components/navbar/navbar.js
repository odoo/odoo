import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

import { OrderTrackerDropdown } from "@point_of_sale/app/components/order_tracker_dropdown/order_tracker_dropdown";
import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { BurgerMenuDialog } from "@point_of_sale/app/components/navbar/burger_menu/burger_menu_dialog";
import { Component, proxy, signal, useListener } from "@odoo/owl";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { barcodeService } from "@barcodes/barcode_service";
import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { _t } from "@web/core/l10n/translation";
import { isPrivateIp } from "@point_of_sale/utils";
import { QrCodeCustomerDisplay } from "@point_of_sale/app/customer_display/customer_display_qr_code_popup";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
export { BurgerMenuDialog };

export class Navbar extends Component {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        SaleDetailsButton,
        Input,
        OrderTabs,
        OrderTrackerDropdown,
    };
    inputRef = signal.ref();
    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.state = proxy({ searchBarOpen: false });
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.isBarcodeScannerSupported = isBarcodeScannerSupported;
        this.timeout = null;
        this.bufferedInput = "";
        useListener(document, "keydown", this.handleKeydown.bind(this));
        this.openPresetTiming = useAsyncLockedMethod(this.openPresetTiming.bind(this));
    }

    async openLnaPopup() {
        let localPrinterIp;
        for (const printer of [
            ...this.pos.config.receipt_printer_ids,
            ...this.pos.config.preparation_printer_ids,
        ]) {
            if (isPrivateIp(printer.printer_ip)) {
                localPrinterIp = printer.printer_ip;
                break;
            }
        }
        if (localPrinterIp) {
            try {
                const protocol = "http:";
                const url = protocol + "//" + localPrinterIp;
                this.address = url + "/cgi-bin/epos/service.cgi?devid=local_printer";
                const params = {
                    method: "POST",
                    body: `<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
                            <s:Body>
                                <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
                                    <feed line="1" />
                                    <text align="center">This is a test receipt&#10;</text>
                                    <feed line="3" />
                                    <cut type="feed" />
                                </epos-print>
                            </s:Body>
                        </s:Envelope>`,
                    signal: AbortSignal.timeout(15000),
                };
                await fetch(this.address, params);
                return;
            } catch {
                console.error("Could not connect to printer");
            }
        }
        this.dialog.add(AlertDialog, {
            title: _t("LNA Permission status"),
            body: this.pos.lnaState.message,
            size: "sm",
            backdrop: true,
        });
    }

    openBurgerMenu() {
        this.dialog.add(BurgerMenuDialog, {
            openCustomerDisplay: this.openCustomerDisplay.bind(this),
            openLnaPopup: this.openLnaPopup.bind(this),
        });
    }

    handleKeydown(event) {
        const isSpecialKey =
            !["Control", "Alt"].includes(event.key) && (event.key?.length > 1 || event.metaKey);

        clearTimeout(this.timeout);
        if (event.key === "Tab") {
            this.checkInput(event);
        } else if (event.key === "Enter") {
            this.checkInput(event);
            if (event.target === this.inputRef()) {
                this.pos.searchProductsFromDB();
            }
        } else {
            if (!isSpecialKey) {
                this.bufferedInput += event.key;
            }
            if (document.activeElement == this.inputRef()) {
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
            this.inputRef() &&
            document.activeElement !== this.inputRef() &&
            !this.pos.getOrder()?.getSelectedOrderline() &&
            this.noOpenDialogs() &&
            event.key?.length == 1 &&
            this.bufferedInput.length < 3
        ) {
            this.inputRef().focus();
            this.inputRef().value = this.bufferedInput;
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

    onTicketButtonClick() {
        // select default selected order and apply paid filter while editing paid order payments
        if (this.pos.router.currentScreen() == "PaymentScreen" && this.pos.getOrder()?.finalized) {
            return this.pos.openFinalizedOrders();
        }
        return this.pos.navigate("TicketScreen");
    }
    noOpenDialogs() {
        return document.querySelectorAll(".modal-dialog, .debug-widget").length === 0;
    }
    onClickScan() {
        this.pos.toggleScanning();
    }
    get showCashMoveButton() {
        return this.pos.showCashMoveButton;
    }
    getOrderTabs() {
        return this.pos.getOpenOrders().filter((order) => !order.table_id);
    }

    openCustomerDisplay() {
        this.dialog.add(QrCodeCustomerDisplay, {
            customerDisplayURL: this.pos.customerDisplayUrl,
        });
    }

    get shouldDisplayPresetTime() {
        return this.pos.getOrder()?.preset_id?.use_timing;
    }

    async openPresetTiming() {
        await this.pos.openPresetTiming();
    }

    get mainButton() {
        const screens = ["ProductScreen", "PaymentScreen", "TipScreen"];
        return screens.includes(this.pos.router.currentScreen()) ? "register" : "order";
    }
    get showOderTrackerDropdown() {
        return false;
    }
}
