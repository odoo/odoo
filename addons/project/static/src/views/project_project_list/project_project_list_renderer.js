/** @odoo-module native */
import { getRawValue } from "@web/views/kanban";
import { ListRenderer } from "@web/views/list";

import { ProjectProjectGroupConfigMenu } from "../project_project_kanban/project_project_group_config_menu.js";

export class ProjectProjectListRenderer extends ListRenderer {
    static rowsDependOnSelection = true;
    static components = {
        ...ListRenderer.components,
        GroupConfigMenu: ProjectProjectGroupConfigMenu,
    };

    /** @returns {boolean} */
    haveAllSelectedProjectsSameField(field) {
        this._sameFieldCache ??= {};
        if (!(field in this._sameFieldCache)) {
            const selection = this.props.list.selection;
            const value = selection.length && getRawValue(selection[0], field);
            this._sameFieldCache[field] = selection.every(
                (project) => getRawValue(project, field) === value,
            );
            Promise.resolve().then(() => {
                delete this._sameFieldCache;
            });
        }
        return this._sameFieldCache[field];
    }

    isCellReadonly(column, record) {
        let readonly = super.isCellReadonly(column, record);
        if (!readonly && column.name === "phase_id") {
            readonly = !this.haveAllSelectedProjectsSameField("company_id");
        }
        return readonly;
    }
}
