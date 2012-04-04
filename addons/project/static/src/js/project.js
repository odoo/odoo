openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this
            self._super()
            if(this.view.dataset.model == 'project.project') {
                $('.oe_project_kanban_vignette').mouseover(function() {
                    return $(this).find('.oe_project_kanban_action').show();
                    }).mouseout(function() {
                    return $(this).find('.oe_project_kanban_action').hide();
                });
                $('.dropdown-toggle').dropdown();
                $('.oe_project_kanban_action').click(function(){
                     $('.dropdown-toggle').dropdown();
                 })
            }
        }
    });
}
