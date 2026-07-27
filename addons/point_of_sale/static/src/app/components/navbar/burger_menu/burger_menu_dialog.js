import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";

export class BurgerMenuDialog extends Component {
    static template = "point_of_sale.BurgerMenuDialog";
    static components = { Dialog };
    props = useProps({
        openCustomerDisplay: t.function(),
        openLnaPopup: t.function(),
        close: t.function(),
    });

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.isDisplayStandalone = isDisplayStandalone();
        this.isBarcodeScannerSupported = isBarcodeScannerSupported;
    }

    get appUrl() {
        return `/scoped_app?app_id=point_of_sale&app_name=${encodeURIComponent(
            this.pos.config.display_name
        )}&path=${encodeURIComponent(`pos/ui/${this.pos.config.id}`)}`;
    }

    get showCashMoveButton() {
        return this.pos.showCashMoveButton;
    }

    get showCreateProductButton() {
        return this.pos.hasProductCreationAccess;
    }

    get showPrinterButton() {
        return this.pos.config.other_devices && this.pos.config.receipt_printer_ids.length > 1;
    }

    openLnaPopup() {
        this.props.openLnaPopup();
        this.props.close();
    }

    onClickScan() {
        this.pos.toggleScanning();
    }

    async showSaleDetails() {
        await this.pos.ticketPrinter.printSaleDetailsReceipt();
    }

    closeAndRun(fn) {
        this.props.close();
        fn();
    }
}
