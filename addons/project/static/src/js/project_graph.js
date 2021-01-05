odoo.define('project.ProjectGraphView', function (require) {
    "use strict";
    
    const GraphView = require('web.GraphView');
    const viewRegistry = require('web.view_registry');
    const ProjectControlPanel = require("project.ProjectControlPanel");

    const ProjectGraphView = GraphView.extend({
            config: _.extend({}, GraphView.prototype.config, {
                ControlPanel: ProjectControlPanel,
            }),
        });
    
    viewRegistry.add('project_graph', ProjectGraphView);
    return ProjectGraphView;
});
