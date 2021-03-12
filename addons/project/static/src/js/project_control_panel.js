odoo.define("project.ProjectControlPanel", function (require) {
    "use strict";

    const ControlPanel = require("web.ControlPanel");
    class ProjectControlPanel extends ControlPanel {

        constructor() {
            super(...arguments);
            this.show_project_update = this.env.view.type === "form" || this.props.action.context.show_project_update;
            this.project_id = this.show_project_update ? this.props.action.context.active_id : false;
        }

        async willStart() {
            const promises = [];
            promises.push(super.willStart(...arguments));
            promises.push(this._loadWidgetData());
            return Promise.all(promises);
        }

        async willUpdateProps() {
            const promises = [];
            promises.push(super.willUpdateProps(...arguments));
            promises.push(this._loadWidgetData());
            return Promise.all(promises);
        }

        async _loadWidgetData() {
            if (this.show_project_update) {
                this.data = await this.rpc({
                    model: 'project.project',
                    method: 'get_last_update_or_default',
                    args: [this.project_id],
                });
            }
        }

        async onStatusClick(ev) {
            ev.preventDefault();
            this.trigger('do-action', {
                action: "project.project_update_all_action",
                options: {
                    additional_context: this.props.action.context
                }
            });
        }

    }
    ProjectControlPanel.template = "project.ControlPanel";

    return ProjectControlPanel;
});
