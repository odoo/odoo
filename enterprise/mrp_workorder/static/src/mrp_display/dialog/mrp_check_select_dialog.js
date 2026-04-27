/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class MrpQualityCheckSelectDialog extends ConfirmationDialog {
    static template = "mrp_workorder.MrpQualityCheckSelectDialog";
    static props = {
        ...ConfirmationDialog.props,
        body: { type: String, optional: true },
        checks: { type: Array, optional: true },
        type: { type: String, optional: true }
    };

    setup() {
        super.setup();
        this.checks = [];
        for (const check of this.props.checks || []) {
            this.checks.push({
                id: parseInt(check.resId),
                display_name: check.data.title,
            });
        }
    }

    selectCheck(qc) {
        this.props.confirm(this.props.type, qc);
        this.props.close();
    }
}
