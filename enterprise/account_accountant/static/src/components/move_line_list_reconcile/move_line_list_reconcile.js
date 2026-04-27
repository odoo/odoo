/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useSubEnv } from "@odoo/owl";
import { AccountMoveLineListController, AccountMoveLineListRenderer, AccountMoveLineListView } from "../move_line_list/move_line_list";


export class AccountMoveLineReconcileListController extends AccountMoveLineListController {

    setup() {
        super.setup();
        useSubEnv({
            callAutoReconcileAction: this.openAutoReconcileWizard.bind(this),
        });
    }

    openAutoReconcileWizard(group=null) {
        if (group) {
            return this.actionService.doAction("account_accountant.action_open_auto_reconcile_wizard", {
                additionalContext: {
                    domain: group.list.domain,
                }
            });
        } else {
            return this.actionService.doAction("account_accountant.action_open_auto_reconcile_wizard");
        }
    }
}

export class AccountMoveLineReconcileListRenderer extends AccountMoveLineListRenderer {

    static groupRowTemplate = "account_accountant.AccountMoveLineReconcileGroupRow";

    setup() {
        super.setup();
        this.props.list.groups?.map(group => this.toggleGroup(group));  // unfold the first groups (account_id)
    }

}

export const AccountMoveLineReconcileLineListView = {
    ...AccountMoveLineListView,
    Controller: AccountMoveLineReconcileListController,
    Renderer: AccountMoveLineReconcileListRenderer,
    buttonTemplate: "account_accountant.ListViewReconcile.Buttons",
}

registry.category("views").add("account_move_line_reconcile_list", AccountMoveLineReconcileLineListView);
