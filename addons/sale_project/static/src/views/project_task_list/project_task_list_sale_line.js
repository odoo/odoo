/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProjectTaskListRenderer } from "@project/views/project_task_list/project_task_list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";

patch(ProjectTaskListRenderer.prototype, {
    isCellReadonly(column, record) {
        const readonly = super.isCellReadonly(column, record);
        const selection = this.props.list.selection;
        if (column.name === "sale_line_id" && selection.length) {
            const partnerId = getRawValue(selection[0], "partner_id");
            return readonly || selection.some(
                (task) => getRawValue(task, "partner_id") !== partnerId
            );
        }
        return readonly;
    },
});
