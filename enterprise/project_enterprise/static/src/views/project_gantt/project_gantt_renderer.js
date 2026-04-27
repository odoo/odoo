import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { GanttRenderer } from "@web_gantt/gantt_renderer";

export class ProjectGanttRenderer extends GanttRenderer {
    static components = {
        ...GanttRenderer.components,
        Avatar,
    };
    static rowHeaderTemplate = "project_enterprise.ProjectGanttRenderer.RowHeader";

    computeDerivedParams() {
        this.rowsWithAvatar = {};
        super.computeDerivedParams();
    }

    processRow(row) {
        const { groupedByField, name, resId } = row;
        if (groupedByField === "user_id" && Boolean(resId)) {
            const { fields } = this.model.metaData;
            const resModel = fields.user_id.relation;
            this.rowsWithAvatar[row.id] = { resModel, resId, displayName: name };
        }
        return super.processRow(...arguments);
    }

    getAvatarProps(row) {
        return this.rowsWithAvatar[row.id];
    }

    hasAvatar(row) {
        return row.id in this.rowsWithAvatar;
    }
}
