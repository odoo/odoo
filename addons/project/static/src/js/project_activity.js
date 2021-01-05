odoo.define('project.ProjectActivityView', function (require) {
    "use strict";
    
    const ActivityView = require('mail.ActivityView');
    const viewRegistry = require('web.view_registry');
    const ProjectControlPanel = require("project.ProjectControlPanel");

    const ProjectActivityView = ActivityView.extend({
            config: _.extend({}, ActivityView.prototype.config, {
                ControlPanel: ProjectControlPanel,
            }),
        });
    
    viewRegistry.add('project_activity', ProjectActivityView);
    return ProjectActivityView;
});
