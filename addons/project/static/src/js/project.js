openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this
            self._super()
            if(this.view.dataset.model == 'project.project') {
                console.log("this");
            }
        }
    });
}
