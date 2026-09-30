import { patch } from "@web/core/utils/patch";
import { ProjectTaskListRenderer } from "@project/views/project_task_list/project_task_list_renderer";

patch(ProjectTaskListRenderer.prototype, {
    isCellReadonly(column, record) {
        let readonly = false;
        if (column.name === "sale_line_id") {
            readonly = !this.haveAllSelectedTasksSameField('partner_id');
        }
        return readonly || super.isCellReadonly(column, record);
    }
});
