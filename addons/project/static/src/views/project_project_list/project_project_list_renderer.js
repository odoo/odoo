/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";

export class ProjectProjectListRenderer extends ListRenderer {
    isCellReadonly(column, record) {
        let readonly = super.isCellReadonly(column, record);
        const { selection } = this.props.list;
        if (column.name === "stage_id" && selection.length) {
            const companyId = getRawValue(selection[0], "company_id");
            readonly = selection.some(
                (task) => getRawValue(task, "company_id") !== companyId
            );
        }
        return readonly;
    }
}
