openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            $('.dropdown-toggle').dropdown();
            $('.oe_project_kanban_vignette').mouseover(function() {
                return $(this).find('.oe_project_kanban_action').show();
                }).mouseout(function() {
                return $(this).find('.oe_project_kanban_action').hide();
            });
            $('.project_avatar').mouseover(function() {
                avatar = this
                var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, [['id','=',avatar.getAttribute("id")]]);
                dataset.read_slice([]).then(function(result){
                    avatar.setAttribute("title",result[0].name)
                });
            });
            self._super();
        }
    });
}
