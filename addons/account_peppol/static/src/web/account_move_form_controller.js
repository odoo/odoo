import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AccountMoveFormController } from "@account/components/account_move_form/account_move_form";

const SALE_MOVE_TYPES = ['out_invoice', 'out_refund', 'out_receipt'];

/**
 * Mirrors the `_check_draftable` and `_unlink_except_sent_peppol` conditions of `account.move`:
 * an invoice sent via Peppol / PDP can neither be reset to draft nor deleted.
 */
export function isSentInvoice(record) {
    return record.peppol_is_sent && SALE_MOVE_TYPES.includes(record.move_type);
}


patch(AccountMoveFormController.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
    },

    _showPeppolConfirmation(message, actionMethod, confirmLabel, successMessage) {
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Peppol Documents: Cannot Delete Invoice"),
            body: message,
            confirm: async () => {
                const record = this.model.root.data;
                await this.model.orm.call('account.move', actionMethod, [[record.id]]);
                this.notification.add(successMessage, { type: 'success' });
                await this.model.root.load();
                this.model.notify();
            },
            cancel: () => {},
            confirmLabel: confirmLabel,
            cancelLabel: _t("No, Keep It"),
        });
    },

    async deleteRecord() {
        const model = this.model.root.resModel;

        if (model === 'account.move') {
            const record = this.model.root.data;

            if (isSentInvoice(record)) {
                // A sent invoice can neither be deleted nor reset to draft: the only way out is
                // a credit or debit note. Cancelling it stays possible from the header button.
                this.dialogService.add(AlertDialog, {
                    title: _t("Peppol Documents: Cannot Delete Invoice"),
                    body: _t(
                        "Invoices sent via Peppol / PDP cannot be deleted.\n\n" +
                        "If you need to modify this one, you must issue a credit or debit note."
                    ),
                });
                return;
            }

            if (record.peppol_message_uuid && record.state !== 'cancel') {
                if (record.state === 'draft') {
                    this._showPeppolConfirmation(
                        _t(
                            "Documents sent/received via Peppol cannot be deleted.\n\n" +
                            "Would you like to cancel this document instead?"
                        ),
                        'action_peppol_cancel_and_remove_sequence',
                        _t("Yes, Cancel It"),
                        _t("Document cancelled successfully")
                    );
                } else {
                    this._showPeppolConfirmation(
                        _t(
                            "Documents sent/received via Peppol cannot be deleted.\n\n" +
                            "Would you like to reset this document to draft instead?"
                        ),
                        'button_draft',
                        _t("Reset to draft"),
                        _t("Document reset to draft successfully")
                    );
                }
                return;
            }
        }

        return super.deleteRecord(...arguments);
    }
});
