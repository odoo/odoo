openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            if(this.view.dataset.model == 'project.project') {
                //open dropdwon when click on the icon.
                $('.dropdown-toggle').dropdown();
                
                //show and hide the dropdown icon when mouseover and mouseour.
                $('.oe_project_kanban_vignette').mouseover(function() {
                    return $(this).find('.oe_project_kanban_action').show();
                    }).mouseout(function() {
                    return $(this).find('.oe_project_kanban_action').hide();
                });
                
                //set avatar title for members.
                _.each($(this.$element).find('.project_avatar'),function(avatar){
                    console.log(avatar.id)
                    var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, [['id','=',avatar.id]]);
                        dataset.read_slice([]).then(function(result){
                            avatar.setAttribute("title",result[0].name)
                    });
                 });
                
                //if task is true , then open the task when clickd on the anywhere in the box.
                if(this.record.task.raw_value)$(this.$element).find('.click_button').attr('data-name','open_tasks');
                if(!this.record.task.raw_value)$(this.$element).find('.click_button').attr('data-name','dummy');
            };
            self._super();
        }
    });
}
