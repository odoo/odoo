/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";

export class ProjectTaskListRenderer extends ListRenderer {
    getCellReadonly(column, record) {
        let readonly = false;
        if (column.name === "stage_id" && this.props.list.selection.length) {
            const projectId = getRawValue(this.props.list.selection[0], "project_id");
            readonly = this.props.list.selection.some(
                (task) => getRawValue(task, "project_id") !== projectId
            );
        }
        return readonly || super.getCellReadonly(column, record);
    }
}
