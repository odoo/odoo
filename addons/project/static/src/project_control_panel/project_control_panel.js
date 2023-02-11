/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useService } from "@web/core/utils/hooks";

export class ProjectControlPanel extends ControlPanel {
    constructor() {
        super(...arguments);
        this.orm = useService("orm");
        this.user = useService("user");
        const { active_id, show_project_update } = this.env.searchModel.globalContext;
        this.showProjectUpdate = this.env.config.viewType === "form" || show_project_update;
        this.projectId = this.showProjectUpdate ? active_id : false;
    }

    async willStart() {
        const proms = [super.willStart(...arguments)];
        if (this.showProjectUpdate) {
            proms.push(this.loadData());
        }
        await Promise.all(proms);
    }

    async willUpdateProps() {
        const proms = [super.willUpdateProps(...arguments)];
        if (this.showProjectUpdate) {
            proms.push(this.loadData());
        }
        await Promise.all(proms);
    }

    async loadData() {
        const [data, isProjectUser] = await Promise.all([
            this.orm.call("project.project", "get_last_update_or_default", [this.projectId]),
            this.user.hasGroup("project.group_project_user"),
        ]);
        this.data = data;
        this.isProjectUser = isProjectUser;
    }

    async onStatusClick(ev) {
        ev.preventDefault();
        this.actionService.doAction("project.project_update_all_action", {
            additionalContext: {
                default_project_id: this.projectId,
                active_id: this.projectId,
            },
        });
    }
}

ProjectControlPanel.template = "project.ProjectControlPanel";
