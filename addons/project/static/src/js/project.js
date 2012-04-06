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
            $('.click_button').attr('data-name','open_tasks');
            	
            _.each($('.oe_project_kanban_vignette'),function(record){
                _.each(record.getElementsByTagName('img'),function(img){
                    var domain = [['id','=',img.getAttribute("id")]]; 
                    var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, domain);
                    dataset.read_slice([]).then(function(result){
                        img.setAttribute("title",result[0].name)
                    });
                });
                
            });
            
        }
    });
}
