/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";
import { _t } from "@web/core/l10n/translation";

export class ProjectTaskListRenderer extends ListRenderer {
    /**
     * This method prevents from computing the selection once for each cell when
     * rendering the list. Indeed, `selection` is a getter which browses all
     * records, so computing it for each cell slows down the rendering a lot on
     * large tables. Moreover, it also prevents from iterating over the selection
     * to compare tasks' projects.
     *
     * It returns true iff the selected tasks are all in the same project.
     */
    areSelectedTasksInSameProject() {
        if (this._areSelectedTasksInSameProject === undefined) {
            const selection = this.props.list.selection;
            const projectId = selection.length && getRawValue(selection[0], "project_id");
            this._areSelectedTasksInSameProject = selection.every(
                (task) => getRawValue(task, "project_id") === projectId
            );
            Promise.resolve().then(() => {
                delete this._areSelectedTasksInSameProject;
            });
        }
        return this._areSelectedTasksInSameProject;
    }
    isCellReadonly(column, record) {
        let readonly = false;
        if (column.name === "stage_id") {
            readonly = !this.areSelectedTasksInSameProject();
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
