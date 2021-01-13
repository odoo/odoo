odoo.define('project.ProjectUpdateView', function (require) {
    "use strict";

    var KanbanView = require('web.KanbanView');
    var view_registry = require('web.view_registry');
    var KanbanRenderer = require('web.KanbanRenderer');


    var ProjectUpdateKanbanRenderer = KanbanRenderer.extend({
        // right side panel to see project.project infos
        
        // create a template t t-name="kanban-right-panel"
        // after the super._renderView, render :
        // this.qweb.render('kanban-right-panel', this.qweb_context);
        // The mechanism should look like the kanban records      
        // Maybe could it be extended to all views (Like SearchPanel (????)
    });

    var ProjectUpdateKanbanView = KanbanView.extend({
        searchMenuTypes: ['filter', 'favorite'],
        config: _.extend({}, KanbanView.prototype.config, {
            Renderer: ProjectUpdateKanbanRenderer,
        }),
    });

    view_registry.add('project_update_kanban', ProjectUpdateKanbanView);

    return ProjectUpdateKanbanView;
});
