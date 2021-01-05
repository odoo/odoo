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

        _loadWidgetData() {
            var self = this;
            return this.rpc({
                model: 'project.project',
                method: 'get_last_update_or_default',
                args: [this.project_id],
            }).then(data => {
                self.data = data;
            });
        }

        onStatusClick(ev) {
            ev.preventDefault();
            var self = this;
            return this.rpc({
                model: 'project.project',
                method: 'action_open_update_status',
                args: [this.project_id],
            }).then(action => {
                self.trigger('do-action', {
                    action: action
                });
            });
        }

    }
    ProjectControlPanel.template = "project.ControlPanel";

    return ProjectControlPanel;
});
