import { Component, onWillStart } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";

export class BadgeScanner extends Component {
    static template = "hr.BadgeScannerTemplate"
    static components = { BarcodeScanner };
    static props = { ...standardActionServiceProps };
    setup() {
        this.employeeId = this.props.action?.params?.employeeId;
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        if (!this.employeeId) {
            this.notification.add(_t("Missing Employee ID"), {
                title: _t("Warning"),
                type: "danger",
            });
            throw new Error(_t("Cannot scan badge without employee ID"));
        }
        this.employee = await this.orm.read("hr.employee", [this.employeeId], ["name"]);
    }

    onBarcodeScanned(barcode) {
        if (!barcode) {
            this.notification.add(_t("No barcode received"), {
                title: _t("Warning"),
                type: "danger",
            });
            return;
        }
        if (!this.employeeId) {
            this.notification.add(_t("Missing Employee ID"), {
                title: _t("Warning"),
                type: "danger",
            });
            return;
        }
        this.orm.call("hr.employee", "write", [[this.employee[0].id], {
            barcode: barcode,
        }]).then(() => {
            this.env.config.historyBack();
            this.notification.add((_t("Badge updated: ") + barcode), { type: "success" });
        }).catch(() => {
            this.notification.add(_t("Failed to update badge"), {
                title: _t("Error"),
                type: "danger",
            });
        });
    }
    onClickBack() {
        this.env.config.historyBack();
    }
}

registry.category("actions").add("simple_barcode_scanner", BadgeScanner);
