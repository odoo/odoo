openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            self._super();
            $('.dropdown-toggle').dropdown();
            $('.oe_project_kanban_vignette').mouseover(function() {
                return $(this).find('.oe_project_kanban_action').show();
                }).mouseout(function() {
                return $(this).find('.oe_project_kanban_action').hide();
            });
            
            
            $('.click_button').mouseover(function() {
                click_button = this
                var domain = [['id','=',this.getAttribute("id")]]; 
                var dataset = new openerp.web.DataSetSearch(self, 'project.project', self.session.context, domain);
                dataset.read_slice([]).then(function(result){
                    if(result[0].task){
                        click_button.setAttribute('data-name','open_tasks');
                    }
                    else
                    {
                        click_button.setAttribute('data-name','dummy');
                    }
                    });
            });
            	
            $('.project_avatar').mouseover(function() {
                avatar = this
                var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, [['id','=',avatar.getAttribute("id")]]);
                dataset.read_slice([]).then(function(result){
                    avatar.setAttribute("title",result[0].name)
                });
            });
            
        }
    });
}
