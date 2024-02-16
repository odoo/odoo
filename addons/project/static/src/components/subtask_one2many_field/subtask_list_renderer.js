/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ListRenderer } from '@web/views/list/list_renderer';

import { useEffect } from "@odoo/owl";

export class SubtaskListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        useEffect(
            () => this.focusName(this.props.list.editedRecord),
            () => [this.props.list.editedRecord]
        );
    }

    focusName(editedRecord) {
        if (editedRecord?.isNew && !editedRecord.dirty) {
            const col = this.columns.find((c) => c.name === "name");
            this.focusCell(col);
        }
    }

    // Override the displayed text on subtask tooltip.
    getCellTitle(column, record) {
        let cellTitle = super.getCellTitle(column, record);
        // Add subtask count to the tooltip of the name (title) column.
        if (cellTitle && column.name === "name" && (record.data.closed_subtask_count || record.data.subtask_count)) {
            cellTitle += ` (${record.data.closed_subtask_count}/${record.data.subtask_count}) sub-tasks`;
        }
        // Hide the tooltip on the project's column if the display_in_project is False.
        else if (cellTitle && column.name === "project_id" && record.data.display_in_project == false) {
            cellTitle = '';
        }
        return cellTitle;
    }

    async onDeleteRecord(record) {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this record?"),
            confirm: () => super.onDeleteRecord(record),
            cancel: () => {},
        });
    }
}
