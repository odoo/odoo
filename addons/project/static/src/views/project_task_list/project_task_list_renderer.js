import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";
import { ProjectTaskGroupConfigMenu } from "../project_task_kanban/project_task_group_config_menu";

export class ProjectTaskListRenderer extends ListRenderer {
    static components = {
        ...ListRenderer.components,
        GroupConfigMenu: ProjectTaskGroupConfigMenu,
    };

    /**
     * This method prevents from computing the selection once for each cell when
     * rendering the list. Indeed, `selection` is a getter which browses all
     * records, so computing it for each cell slows down the rendering a lot on
     * large tables. Moreover, it also prevents from iterating over the selection
     * to compare tasks' projects or partners.
     *
     * Returns true if all selected tasks have the same value for the specified field.
     */
    haveAllSelectedTasksSameField(field) {
        if (this._areSelectedTasksInSameProject === undefined) {
            const selection = this.props.list.selection;
            const projectId = selection.length && getRawValue(selection[0], field);
            this._areSelectedTasksInSameProject = selection.every(
                (task) => getRawValue(task, field) === projectId
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
            readonly = !this.haveAllSelectedTasksSameField('project_id');
        }
        return readonly || super.isCellReadonly(column, record);
    }
}
