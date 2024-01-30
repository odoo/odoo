/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { escape } from "@web/core/utils/strings";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";


export const accountMove = {
    dependencies: ["dialog", "orm"],
    start(env, { dialog, orm }) {
        return {
            async addDeletionDialog(component, moveIds) {
                const isMoveEndOfChain = await orm.call('account.move', 'check_move_sequence_chain', [moveIds]);
                if (!isMoveEndOfChain) {
                    const message = env._t("This operation will create a gap in the sequence.");
                    const confirmationDialogProps = component.deleteConfirmationDialogProps;
                    confirmationDialogProps.body = markup(`<div class="text-danger">${escape(message)}</div>${escape(confirmationDialogProps.body)}`);
                    dialog.add(ConfirmationDialog, confirmationDialogProps);
                    return true;
                }
                return false;
            }
        }
    }
}

registry.category("services").add("account_move", accountMove);
