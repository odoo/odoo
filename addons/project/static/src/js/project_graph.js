/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { GraphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/service_hook";

const viewRegistry = registry.category("views");

class ProjectControlPanel extends ControlPanel {
    constructor() {
        super(...arguments);
        this._ormService = useService("orm");
        this._userService = useService("user");
        const { active_id, show_project_update } = this.env.searchModel.globalContext;
        this.showProjectUpdate =
            /** @todo see how to have this working */
            // this.env.view.type === "form" || hum view.type is not there
            show_project_update;
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
        this.data = await this._ormService.call("project.project", "get_last_update_or_default", [
            this.projectId,
        ]);
        this.isProjectManager = this._userService.hasGroup("project.group_project_manager");
    }

    async onStatusClick(ev) {
        ev.preventDefault();
        this._actionService.doAction("project.project_update_all_action", {
            additional_context: {
                default_project_id: this.projectId,
                active_id: this.projectId,
            },
        });
    }
}
ControlPanel.template = "web.ControlPanel"; /** @todo should be something good that inherits from web.ControlPanel */

class ProjectGraphView extends GraphView {}
GraphView.ControlPanel = ProjectControlPanel;

viewRegistry.add("project_graph", ProjectGraphView);
