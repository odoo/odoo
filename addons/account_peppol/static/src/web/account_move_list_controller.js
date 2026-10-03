import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AccountMoveListController } from "@account/views/account_move_list/account_move_list_controller";
import { isSentInvoice } from "@account_peppol/web/account_move_form_controller";


patch(AccountMoveListController.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
    },

    async onDeleteSelectedRecords() {
        const model = this.model.root.resModel;

        if (model === 'account.move') {
            const selectedRecords = this.model.root.selection;
            const selectedIds = selectedRecords.map(rec => rec.resId);

            const recordsData = await this.model.orm.read(
                'account.move',
                selectedIds,
                ['peppol_message_uuid', 'name', 'display_name', 'state', 'peppol_is_sent', 'move_type']
            );

            const peppolRecords = recordsData.filter(rec => rec.peppol_message_uuid);
            // Sent invoices can neither be reset to draft nor deleted: they are left untouched.
            const sentPeppol = peppolRecords.filter(isSentInvoice);
            const untouchedIdSet = new Set(sentPeppol.map(rec => rec.id));
            const nonCancelledPeppol = peppolRecords.filter(rec => rec.state !== 'cancel' && !untouchedIdSet.has(rec.id));

            if (nonCancelledPeppol.length > 0 || sentPeppol.length > 0) {
                const peppolIdSet = new Set(peppolRecords.map(r => r.id));
                const cancelledPeppolIds = peppolRecords
                    .filter(rec => rec.state === 'cancel' && !untouchedIdSet.has(rec.id))
                    .map(r => r.id);
                const toDeleteIds = [
                    ...selectedIds.filter(id => !peppolIdSet.has(id)),
                    ...cancelledPeppolIds,
                ];

                const draftPeppol = nonCancelledPeppol.filter(rec => rec.state === 'draft');
                const postedPeppol = nonCancelledPeppol.filter(rec => rec.state !== 'draft');

                const label = rec => rec.name || rec.display_name;
                const sections = [];

                if (sentPeppol.length > 0) {
                    sections.push(_t(
                        "The following %s document(s) were sent via Peppol / PDP and will be left "
                        + "untouched. If you need to modify them, you must issue a credit or debit "
                        + "note:\n\n• %s",
                        sentPeppol.length,
                        sentPeppol.map(label).join('\n• ')
                    ));
                }
                if (postedPeppol.length > 0) {
                    sections.push(_t(
                        "The following %s Peppol document(s) will be reset to draft:\n\n• %s",
                        postedPeppol.length,
                        postedPeppol.map(label).join('\n• ')
                    ));
                }
                if (draftPeppol.length > 0) {
                    sections.push(_t(
                        "The following %s draft Peppol document(s) will be cancelled:\n\n• %s",
                        draftPeppol.length,
                        draftPeppol.map(label).join('\n• ')
                    ));
                }

                if (toDeleteIds.length > 0) {
                    sections.push(_t("The remaining %s document(s) will be deleted.", toDeleteIds.length));
                }
                if (nonCancelledPeppol.length === 0 && toDeleteIds.length === 0) {
                    // Everything that was selected must be left untouched: nothing to confirm.
                    this.dialogService.add(AlertDialog, {
                        title: _t("Peppol Documents Cannot Be Deleted"),
                        body: sections.join('\n\n'),
                    });
                    return;
                }

                sections.push(_t("Do you want to proceed?"));
                const message = sections.join('\n\n');

                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Peppol Documents Cannot Be Deleted"),
                    body: message,
                    confirm: async () => {
                        await this.model.orm.call('account.move', 'action_peppol_reset_documents', [nonCancelledPeppol.map(rec => rec.id), toDeleteIds]);

                        this.notification.add(
                            _t(
                                "%(processed)s Peppol document(s) processed, %(deleted)s document(s) deleted",
                                { processed: nonCancelledPeppol.length, deleted: toDeleteIds.length }
                            ),
                            { type: 'success' }
                        );

                        await this.model.root.load();
                        this.model.notify();
                    },
                    cancel: () => {},
                    confirmLabel: _t("Yes, Proceed"),
                    cancelLabel: _t("Cancel"),
                });

                return;
            }
        }

        return super.onDeleteSelectedRecords(...arguments);
    }
});
