import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class MailingTemplateKanbanRecord extends KanbanRecord {
    static template = "mass_mailing.MailingTemplateKanbanRecord";
    static menuTemplate = "mass_mailing.KanbanMenu";
    /**
     * Override
     * Rerender the kanban view when a record is archived.
     */
    async archiveRecord(record, active) {
        if (active) {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Are you sure that you want to archive this record?"),
                confirmLabel: _t("Archive"),
                confirm: async () => {
                    record.archive();
                    return this.props.record.model.root.load();
                },
                cancel: () => {},
            });
        } else {
            record.unarchive();
            return this.props.record.model.root.load();
        }
    }
}
