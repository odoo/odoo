openerp.project_timesheet = function(openerp) {
    openerp.web_kanban.ProjectTimeSheetKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            self._super();
            console.log("project_timesheet :: ",self)
        }
    });
}
