import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AccountMoveFormController } from "@account/components/account_move_form/account_move_form";


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
