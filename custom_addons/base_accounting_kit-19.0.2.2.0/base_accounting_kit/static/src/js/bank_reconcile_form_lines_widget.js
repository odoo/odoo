/** @odoo-module **/
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const { Component, useState, useExternalListener } = owl;
export class BankReconcileFormLinesWidget extends Component {
    setup(){
        super.setup();
        this.state = useState({statementLineResult: null,
                                MoveLineResult:null});
        this.action = useService("action")
        this.orm = useService("orm")
    }
    range(n){
        return[...Array(Math.max(n,0)).keys()];
    }
    get record(){
        return this.props.record;
    }
    async mountStatementLine(ev){
        const manualOpsTab = document.querySelector('[name="manual_operations_tab"]');
        if (manualOpsTab) {
           manualOpsTab.click();
        }
    }
    async onclickLink(ev){
        const id = ev.currentTarget.dataset.id;
        if (id) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'account.move',
                res_id: parseInt(id),
                views: [[false, "form"]],
                target: 'current',
            });
        }
    }
    async removeRecord(ev){
        ev.preventDefault();
        var button = ev.currentTarget;
        var row = button.closest('tr');
        var firstRow = document.querySelector('.o_data_row:first-child');
        var data_id = firstRow.dataset.id;
        try {
            await this.orm.call('account.bank.statement.line', 'write', [[parseInt(data_id)], {'lines_widget_json': null}]);
            // Update the UI or perform any other actions as needed
        } catch (error) {
            console.error('Error removing lines_widget_json:', error);
            // Handle the error as needed
        }
        row.remove();
    }
    getRenderValues(){
        var self=this;
        let data = this.props.record.context
        this.orm.call('account.bank.statement.line', 'update_rowdata', [this.props.record.data.id])
        let columns=[
            ["account",_t("Account")],
            ["partner",_t("Partner")],
            ["date",_t("Date")],
        ];
        if(data.display_analytic_account_column){
            columns.push(["analytic_account", _t("Analytic Account")]);
        }
        if(data.display_multi_currency_column){
            columns.push(["amount_currency", _t("Amount in Currency")], ["currency", _t("Currency")]);
        }
        if(data.display_taxes_column){
            columns.push(["taxes", _t("Taxes")]);
        }
        columns.push(["debit", _t("Debit")], ["credit", _t("Credit")], ["__trash", ""]);
        return {...data,columns:columns}
    }
}
BankReconcileFormLinesWidget.template = 'base_accounting_kit.bank_reconcile_widget_lines_widget';
export const FormLines = {
    component: BankReconcileFormLinesWidget
}
registry.category("fields").add('bank_reconcile_widget_lines_widget', FormLines)
