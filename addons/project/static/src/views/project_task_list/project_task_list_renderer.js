/** @odoo-module native */
import { getRawValue } from "@web/views/kanban";
import { ListRenderer } from "@web/views/list";

import { ProjectTaskGroupConfigMenu } from "../project_task_kanban/project_task_group_config_menu.js";

export class ProjectTaskListRenderer extends ListRenderer {
    static rowsDependOnSelection = true;
    static components = {
        ...ListRenderer.components,
        GroupConfigMenu: ProjectTaskGroupConfigMenu,
    };

    haveAllSelectedTasksSameField(field) {
        this._sameFieldCache ??= {};
        if (!(field in this._sameFieldCache)) {
            const selection = this.props.list.selection;
            const value = selection.length && getRawValue(selection[0], field);
            this._sameFieldCache[field] = selection.every(
                (task) => getRawValue(task, field) === value,
            );
            Promise.resolve().then(() => {
                delete this._sameFieldCache;
            });
        }
        return this._sameFieldCache[field];
    }
    isCellReadonly(column, record) {
        let readonly = false;
        if (column.name === "step_id") {
            readonly = !this.haveAllSelectedTasksSameField("project_id");
        }
        return readonly || super.isCellReadonly(column, record);
    }
}
