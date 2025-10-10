import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NotebookTaskListRenderer } from '../notebook_task_one2many_field/notebook_task_list_renderer';

export class SubtaskListRenderer extends NotebookTaskListRenderer {
    async onDeleteRecord(record) {
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Delete Subtask"),
                body: _t("Are you sure you want to delete this subtask? All its content will be lost."),
                confirmLabel: _t("Delete"),
                confirm: () => super.onDeleteRecord(record).then(resolve),
                cancel: resolve,
            });
        });
    }
}
