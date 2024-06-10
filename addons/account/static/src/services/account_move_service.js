/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { escape } from "@web/core/utils/strings";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";


export const accountMove = {
    dependencies: ["action", "dialog", "orm"],
    start(env, { action, dialog, orm }) {
        return {
            async addDeletionDialog(component, moveIds) {
                const isMoveEndOfChain = await orm.call('account.move', 'check_move_sequence_chain', [moveIds]);
                if (!isMoveEndOfChain) {
                    const message = _t("This operation will create a gap in the sequence.");
                    const confirmationDialogProps = component.deleteConfirmationDialogProps;
                    confirmationDialogProps.body = markup(`<div class="text-danger">${escape(message)}</div>${escape(confirmationDialogProps.body)}`);
                    dialog.add(ConfirmationDialog, confirmationDialogProps);
                    return true;
                }
                return false;
            },
            async downloadPdf(accountMoveId) {
                const downloadAction = await orm.call(
                    "account.move",
                    "action_invoice_download_pdf",
                    [accountMoveId]
                );
                await action.doAction(downloadAction);
            },
        };
    },
};

registry.category("services").add("account_move", accountMove);
