/** @odoo-module **/

import {
    AccountMoveKanbanController,
} from "@account/views/account_move_kanban/account_move_kanban_controller";
import {
    AccountMoveListController,
} from "@account/views/account_move_list/account_move_list_controller";
import { Component, onWillStart, useSubEnv } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";


export class BillQrScan extends Component {

    static template = "l10n_in_qr_code_bill_scan.billScanInput";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.actionService = useService('action');
        this.notificationService = useService("notification");
        this.barcodeService = useService('barcode');
        this.orm = useService("orm");
        useBus(this.barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScanned(ev));
        onWillStart(async () => {
            this.isMobileScanner = isBarcodeScannerSupported();
        });
    }

    async openMobileScanner() {
        const barcode = await scanBarcode(this.env);
        if (barcode) {
            this.barcodeService.bus.trigger('barcode_scanned', { barcode });
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.env.services.notification.add(_t("Please, Scan again!"), {
                type: 'warning'
            });
        }
    }

    async _onBarcodeScanned(ev) {
        this.env.services.ui.block();
        try {
            const res = await this.orm.call(
                "account.move", "l10n_in_get_bill_from_qr_raw", [], { qr_raw: ev?.detail?.barcode }
            );
            this.actionService.doAction(res);
            if (res?.params?.type !== 'danger') {
                return this.props.close();
            }
        } finally {
            this.env.services.ui.unblock();
        }
    }
}
registry.category('actions').add('l10n_in_bill_qr_code_scan', BillQrScan);

export function qrBillScannerController() {
    return {
        setup() {
            super.setup();
            this.dialog = useService("dialog");
            this.orm = useService("orm");
            useSubEnv({
                openScanWizard: this.openScanWizard.bind(this),
            });
            onWillStart(async () => {
                const currentCompanyId = this.env.services.company.currentCompany.id;
                this.data = await this.orm.searchRead("res.company", [["id", "=", currentCompanyId]], ["country_code"])
                this.countryCode = this.data[0].country_code;
            });
        },
    
        openScanWizard() {
            this.dialog.add(BillQrScan);
        },

        get isButtonDisplayed() {
            return this.countryCode == 'IN' && ["in_invoice", "in_refund"].includes(this.props.context.default_move_type ?? '')
        },
    }
}

patch(AccountMoveKanbanController.prototype, qrBillScannerController());
patch(AccountMoveListController.prototype, qrBillScannerController());
