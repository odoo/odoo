openerp.project_issue = function(openerp) {
    openerp.web_kanban.ProjectIssueKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            self._super();
            console.log("ISSUES :: ",self)
        }
    });
}
