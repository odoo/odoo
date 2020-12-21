odoo.define("project.ProjectControlPanel", function (require) {
    "use strict";

    const ControlPanel = require("web.ControlPanel");
    class ProjectControlPanel extends ControlPanel {
        constructor() {
            super(...arguments);
        }
    }
    ProjectControlPanel.template = "project.ControlPanel";

    return ProjectControlPanel;
});
