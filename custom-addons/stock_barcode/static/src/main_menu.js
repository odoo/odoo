/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import * as BarcodeScanner from '@web/webclient/barcode/barcode_scanner';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { serializeDate, today } from "@web/core/l10n/dates";
import { Component, onWillStart, useState } from "@odoo/owl";

export class MainMenu extends Component {
    setup() {
        const displayDemoMessage = this.props.action.params.message_demo_barcodes;
        const user = useService('user');
        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        this.home = useService("home_menu");
        this.notificationService = useService("notification");
        this.rpc = useService('rpc');
        this.state = useState({ displayDemoMessage });
        this.barcodeService = useService('barcode');
        useBus(this.barcodeService.bus, "barcode_scanned", (ev) => this._onBarcodeScanned(ev.detail.barcode));
        const orm = useService('orm');

        this.mobileScanner = BarcodeScanner.isBarcodeScannerSupported();

        onWillStart(async () => {
            this.locationsEnabled = await user.hasGroup('stock.group_stock_multi_locations');
            this.packagesEnabled = await user.hasGroup('stock.group_tracking_lot');
            const args = [
                ["user_id", "=?", session.uid],
                ["location_id.usage", "in", ["internal", "transit"]],
                ["inventory_date", "<=", serializeDate(today())],
            ]
            this.quantCount = await orm.searchCount("stock.quant", args);
        });
    }

    async openMobileScanner() {
        const barcode = await BarcodeScanner.scanBarcode(this.env);
        if (barcode){
            this._onBarcodeScanned(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notificationService.add(_t("Please, Scan again!"), { type: 'warning' });
        }
    }

    removeDemoMessage() {
        this.state.displayDemoMessage = false;
        const params = {
            title: _t("Don't show this message again"),
            body: _t("Do you want to permanently remove this message ? " +
                    "It won't appear anymore, so make sure you don't need the barcodes sheet or you have a copy."),
            confirm: () => {
                this.rpc('/stock_barcode/rid_of_message_demo_barcodes');
                location.reload();
            },
            cancel: () => {},
            confirmLabel: _t("Remove it"),
            cancelLabel: _t("Leave it"),
        };
        this.dialogService.add(ConfirmationDialog, params);
    }

    async _onBarcodeScanned(barcode) {
        const res = await this.rpc('/stock_barcode/scan_from_main_menu', { barcode });
        if (res.action) {
            return this.actionService.doAction(res.action);
        }
        this.notificationService.add(res.warning, { type: 'danger' });
    }
}
MainMenu.props = ["action", "actionId", "className"];
MainMenu.props = {
    action: { Object },
    actionId: { type: Number, optional: true },
    className: String,
    globalState: { type: Object, optional: true },
};
MainMenu.template = 'stock_barcode.MainMenu';

registry.category('actions').add('stock_barcode_main_menu', MainMenu);
