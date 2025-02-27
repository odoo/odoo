import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { standardErrorDialogProps } from "@web/core/errors/error_dialogs";
import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";

export class HrContractValidationDialog extends Component {
    static template = "hr_contract.contract_validation_dialog";
    static components = { Dialog };
    static props = {
        ...standardErrorDialogProps,
    };

    setup() {
        const { data, message } = this.props;
        this.title = _t("Odoo Validation");
        if (data && data.arguments && data.arguments.length > 0) {
            this.message = data.arguments[0];
        } else {
            this.message = message;
        }
    }
    async onClose() {
        const { record } = this.props.data
        if (record){
            record.update({ state: record._values.state });
        }
        this.props.close();
    }
}

registry.category("error_dialogs")
        .add("odoo.addons.hr_contract.models.hr_contract.HrContractValidationError", HrContractValidationDialog);
