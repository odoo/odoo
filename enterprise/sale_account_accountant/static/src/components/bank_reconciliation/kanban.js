/** @odoo-module **/
import { patch } from "@web/core/utils/patch";

import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";

patch(BankRecKanbanController.prototype, {

    // -----------------------------------------------------------------------------
    // RPC
    // -----------------------------------------------------------------------------

    async actionRedirectToSaleOrders(){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const { return_todo_command: actionData } = await this.onchange(newState, "redirect_to_matched_sale_orders");
                if(actionData){
                    this.action.doAction(actionData);
                }
            });
        });
    },

});
