odoo.define('project.ProjectPivotView', function (require) {
    "use strict";
    
    const PivotView = require('web.PivotView');
    const viewRegistry = require('web.view_registry');
    const ProjectControlPanel = require("project.ProjectControlPanel");

    const ProjectPivotView = PivotView.extend({
            config: _.extend({}, PivotView.prototype.config, {
                ControlPanel: ProjectControlPanel,
            }),
        });
    
    viewRegistry.add('project_pivot', ProjectPivotView);
    return ProjectPivotView;
});
