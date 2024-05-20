/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TaskListRenderer } from "../task_list_renderer";

export class SubtaskListRenderer extends TaskListRenderer {
    async onDeleteRecord(record) {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this record?"),
            confirm: () => super.onDeleteRecord(record),
            cancel: () => {},
        });
    }
}
