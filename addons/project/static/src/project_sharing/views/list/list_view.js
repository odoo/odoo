import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ProjectTaskControlPanel } from "@project/views/project_task_control_panel/project_task_control_panel";
import { ProjectTaskRelationalModel } from "@project/views/project_task_relational_model";

export class ProjectSharingListRenderer extends ListRenderer {
    /**
     * @override
     * Always hide the gear/cog icon on groups in project sharing
     */
    showGroupConfigMenu(group) {
        return false;
    }
}

const props = listView.props;
listView.props = function (genericProps, view) {
    const result = props(genericProps, view);
    return {
        ...result,
        allowSelectors: false,
    };
};

listView.Model = ProjectTaskRelationalModel;
listView.ControlPanel = ProjectTaskControlPanel;
listView.Renderer = ProjectSharingListRenderer;
