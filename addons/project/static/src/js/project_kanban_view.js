odoo.define('project.project_kanban_view', function (require) {
    "use strict";

    var KanbanView = require('web.KanbanView');
    var ProjectKanbanRenderer = require('project.project_kanban_renderer')
    var ProjectKanbanController = require('project.project_kanban_controller')

    var view_registry = require('web.view_registry');

    var ProjectKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Renderer: ProjectKanbanRenderer,
            Controller: ProjectKanbanController,
        }),
    });

    view_registry.add('project_kanban', ProjectKanbanView);

    return ProjectKanbanView;
});
