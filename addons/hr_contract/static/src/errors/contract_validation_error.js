import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { standardErrorDialogProps } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class HrContractValidationDialog extends Component {
    static template = "hr_contract.contract_validation_dialog";
    static components = { Dialog };
    static props = {
        ...standardErrorDialogProps,
    };

    setup() {
        const { data, message } = this.props;
        this.title = _t("Odoo Validation");
        if (data?.arguments) {
            this.message = data.arguments[0];
        } else {
            this.message = message;
        }
    }
    async onClose() {
        const { record } = this.props.data
        if (record) {
            record.update({ state: record._values.state });
        }
        this.props.close();
    }
}

registry.category("error_dialogs")
        .add("odoo.addons.hr_contract.models.hr_contract.HrContractValidationError", HrContractValidationDialog);
