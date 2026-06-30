import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { BarcodeScanner } from "@barcodes/components/barcode_scanner";

export class BadgeScanner extends Component {
    static template = "hr.BadgeScannerTemplate"
    static components = { BarcodeScanner };
    static props = {
        ...standardActionServiceProps,
    };
    setup() {
        this.employeeId = this.props.action?.context?.active_id;
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.employee = await this.orm.read("hr.employee", [this.employeeId], ["name"]);
        });
    }

    async onBarcodeScanned(barcode) {
        if (!barcode) {
            this.notification.add(_t("No barcode received"), {
                type: "danger",
            });
            return;
        }
        if (!this.employeeId) {
            this.notification.add(_t("Missing Employee ID"), {
                type: "danger",
            });
        }
        try{
            await this.orm.write("hr.employee", [this.employee[0].id], { barcode: barcode })
            this.env.config.historyBack();
            this.notification.add((_t("Badge updated: ") + barcode), { type: "success" });
        }
        catch(error){
            this.notification.add(_t("Failed to update badge: ") + error?.data?.message, {
                type: "danger",
            });
        }
    }

    onClickBack() {
        this.env.config.historyBack();
    }
}

registry.category("actions").add("employee_barcode_scanner", BadgeScanner);
