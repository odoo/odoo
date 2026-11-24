import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AccountMoveListController } from "@account/views/account_move_list/account_move_list_controller";

const SALE_MOVE_TYPES = ['out_invoice', 'out_refund', 'out_receipt'];


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
            const nonCancelledPeppol = peppolRecords.filter(rec => rec.state !== 'cancel');

            if (nonCancelledPeppol.length > 0) {
                const peppolIdSet = new Set(peppolRecords.map(r => r.id));
                const cancelledPeppol = peppolRecords.filter(rec => rec.state === 'cancel');
                // Sent customer invoices cannot be deleted, even when cancelled (see `_unlink_except_peppol_sent`).
                const isSentInvoice = rec => rec.peppol_is_sent && SALE_MOVE_TYPES.includes(rec.move_type);
                const sentPeppol = cancelledPeppol.filter(isSentInvoice);
                const cancelledPeppolIds = cancelledPeppol.filter(rec => !isSentInvoice(rec)).map(r => r.id);
                const toDeleteIds = [
                    ...selectedIds.filter(id => !peppolIdSet.has(id)),
                    ...cancelledPeppolIds,
                ];

                const draftPeppol = nonCancelledPeppol.filter(rec => rec.state === 'draft');
                const postedPeppol = nonCancelledPeppol.filter(rec => rec.state !== 'draft');

                const label = rec => rec.name || rec.display_name;
                const sections = [];

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
                if (sentPeppol.length > 0) {
                    sections.push(_t(
                        "The following %s document(s) cannot be deleted as they were sent via Peppol / PDP:\n\n• %s",
                        sentPeppol.length,
                        sentPeppol.map(label).join('\n• ')
                    ));
                }

                if (toDeleteIds.length > 0) {
                    sections.push(_t("The remaining %s document(s) will be deleted.", toDeleteIds.length));
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
