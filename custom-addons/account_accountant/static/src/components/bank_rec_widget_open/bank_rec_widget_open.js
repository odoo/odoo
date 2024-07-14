/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class OpenBankRecWidget extends Component {
    setup() {
        this.action = useService("action");
    }

    async openBankRec(ev) {
        this.action.doActionButton({
            type: "object",
            resId: this.props.record.resId,
            name: "action_open_bank_reconcile_widget",
            resModel: "account.bank.statement",
        });
    }
}

OpenBankRecWidget.template = "account.OpenBankRecWidget";
registry.category("fields").add("bank_rec_widget_open", {
    component: OpenBankRecWidget,
});
