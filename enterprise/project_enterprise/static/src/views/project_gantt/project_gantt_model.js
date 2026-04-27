import { user } from '@web/core/user';
import { GanttModel } from "@web_gantt/gantt_model";

const COLOR_FIELD = "stage_id";

export class ProjectGanttModel extends GanttModel {
    /**
     * @override
     */
    async load(searchParams) {
        const stagesEnabled = await user.hasGroup("project.group_project_stages");
        if (stagesEnabled && !this.metaData.colorField) {
            // This is equivalent to setting a color attribute for the gantt view, but only when we have read access to
            // the field (i.e. the user has the 'project.group_project_stages' group).
            this.metaData.colorField = COLOR_FIELD;
        }
        await super.load(searchParams);
    }
}
