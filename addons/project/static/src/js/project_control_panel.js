odoo.define("project.ProjectControlPanel", function (require) {
    "use strict";

    const ControlPanel = require("web.ControlPanel");
    class ProjectControlPanel extends ControlPanel {
        constructor() {
            super(...arguments);
            this.show_project_update = this.props.action.context.show_project_update !== undefined && this.props.action.context.show_project_update;
            this.project_id = this.show_project_update ? this.props.action.context.active_id : false;
        }


    }
    ProjectControlPanel.template = "project.ControlPanel";

    return ProjectControlPanel;
});
