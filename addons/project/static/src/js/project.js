openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            $('.dropdown-toggle').dropdown();
            $('.oe_project_kanban_vignette').mouseover(function() {
                return $(this).find('.oe_project_kanban_action').show();
                }).mouseout(function() {
                return $(this).find('.oe_project_kanban_action').hide();
            });
            this._super();
        }
    });
}
