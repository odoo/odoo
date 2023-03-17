/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";

export class ProjectTaskListRenderer extends ListRenderer {
    getCellReadonly(column, record) {
        let readonly = false;
        const selection = this.props.list.selection;
        if (column.name === "stage_id" && selection.length) {
            const projectId = getRawValue(selection[0], "project_id");
            readonly = selection.some(
                (task) => getRawValue(task, "project_id") !== projectId
            );
        }
        return readonly || super.getCellReadonly(column, record);
    }
}
