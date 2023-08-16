/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";
import { _t } from "@web/core/l10n/translation";

export class ProjectTaskListRenderer extends ListRenderer {
    isCellReadonly(column, record) {
        let readonly = false;
        const selection = this.props.list.selection;
        if (column.name === "stage_id" && selection.length) {
            const projectId = getRawValue(selection[0], "project_id");
            readonly = selection.some(
                (task) => getRawValue(task, "project_id") !== projectId
            );
        }
        return readonly || super.isCellReadonly(column, record);
    }

    getGroupDisplayName(group) {
        if (group.groupByField.name === "project_id" && !group.value) {
            return _t("🔒 Private");
        } else if (group.groupByField.name === "user_ids" && !group.value) {
            return _t("👤 Unassigned");
        } else {
            return super.getGroupDisplayName(group);
        }
    }
}
