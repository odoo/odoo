/** @odoo-module **/

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { CardLayout } from "@hr_attendance/components/card_layout/card_layout";
import { Component, onWillStart } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class KioskMode extends Component {
    setup() {
        this.actionService = useService("action");
        this.companyService = useService("company");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.orm = useService("orm");

        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev.detail.barcode));

        this.lockScanner = false;

        onWillStart(this.onWillStart);
        // Make a RPC call every day to keep the session alive
        browser.setInterval(() => this.callServer(), 60 * 60 * 1000 * 24);
    }

    async onWillStart() {
        const companyId = this.companyService.currentCompany.id;
        const currentCompany = (
            await this.orm.searchRead(
                "res.company",
                [["id", "=", companyId]],
                ["name", "attendance_kiosk_mode", "attendance_barcode_source"][
                    ("employee_id", "date_from", "date_to", "number_of_days")
                ]
            )
        )[0];

        this.companyName = currentCompany.name;
        this.companyImageUrl = url("/web/image", {
            model: "res.company",
            id: companyId,
            field: "logo",
        });
        this.kioskMode = currentCompany.attendance_kiosk_mode;
        this.barcodeSource = currentCompany.attendance_barcode_source;
    }

    onClickAttendanceEmployees() {
        this.actionService.doAction("hr_attendance.hr_employee_attendance_action_kanban", {
            additionalContext: { no_group_by: true },
        });
    }

    async onBarcodeScanned(barcode) {
        if (this.lockScanner) {
            return;
        }
        this.lockScanner = true;
        const result = await this.orm.call("hr.employee", "attendance_scan", [barcode]);
        if (result.action) {
            this.actionService.doAction(result.action);
        } else if (result.warning) {
            this.notification.add(result.warning, { type: "danger" });
            this.lockScanner = false;
        }
    }

    callServer() {
        // Make a call to the database to avoid the auto close of the session
        this.rpc("/hr_attendance/kiosk_keepalive", {});
    }
}

class KioskModeBarcodeScanner extends BarcodeScanner {
    get facingMode() {
        if (this.props.barcodeSource == "front") {
            return "user";
        }
        return super.facingMode;
    }
}
KioskModeBarcodeScanner.props = {
    ...BarcodeScanner.props,
    barcodeSource: String,
};

KioskMode.template = "hr_attendance.KioskMode";
KioskMode.components = { CardLayout, BarcodeScanner: KioskModeBarcodeScanner };

registry.category("actions").add("hr_attendance_kiosk_mode", KioskMode);
