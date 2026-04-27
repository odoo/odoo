/** @odoo-module **/
import { Component, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

export class BankRecGlobalInfo extends Component {
    static template = "account_accountant.BankRecGlobalInfo";
    static props = {
        journalId: { type: Number },
        journalBalanceAmount: { type: String },
    };

    setup() {
        this.hasGroupReadOnly = false;
        onWillStart(async () => {
            this.hasGroupReadOnly = await user.hasGroup("account.group_account_readonly");
        })
    }

    /** Open the bank reconciliation report. **/
    actionOpenBankGL() {
        this.env.methods.actionOpenBankGL(this.props.journalId);
    }

}
