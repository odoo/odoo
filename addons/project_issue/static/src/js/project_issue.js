openerp.portal_project_issue = function(openerp) {
    openerp.web_kanban.KanbanView.include({
        on_groups_started: function() {
            var self = this;
            self._super.apply(this, arguments);

            if (self.dataset.model === 'project.issue') {
                // Load project's categories names from m2m field
                self.project_display_categ_names();
            }
        }
    });
};
