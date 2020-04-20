odoo.define('project.project_kanban_renderer', function (require) {
    "use strict";

    var KanbanRenderer = require('web.KanbanRenderer');
    var ProjectKanbanColumn = require('project.project_kanban_column');

    var ProjectKanbanRenderer = KanbanRenderer.extend({
        config: _.extend({}, KanbanRenderer.prototype.config, {
            KanbanColumn: ProjectKanbanColumn,
        }),

        init() {
            this._super.apply(this, arguments);
            this.demo_records = {};
            let self = this;

            this.getSession().user_has_group('project.group_project_rating').then((has_group) => {
                self.rating_enabled = has_group;
            });
        }
    });


    return ProjectKanbanRenderer;
});
