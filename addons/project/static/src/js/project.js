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
                    var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, [['id','=',avatar.id]]);
                    dataset.read_slice([]).then(function(result){
                    avatar.setAttribute("title",result[0].name)
                    });
                 });
                
                //if task is true , then open the task when click on the anywhere in the box.
                if(this.record.task.raw_value)$(this.$element).find('.click_button').attr('data-name','open_tasks');
                if(!this.record.task.raw_value)$(this.$element).find('.click_button').attr('data-name','dummy');
                
                // set sequence like Tasks,Issues,Timesheets and Phases
                my_list = $("#list a")
                my_list.sort(function (a, b) {
                    var aValue = parseInt(a.id);
                    var bValue = parseInt(b.id);
                    // ASC
                    //return aValue == bValue ? 0 : aValue < bValue ? -1 : 1;
                    // DESC
                    return aValue == bValue ? 0 : aValue < bValue ? -1 : 1;
                  });
                $('#list').replaceWith(my_list);
                
                // set background color
                this.$element.find('.bgcolor_steelblue').click(function(){
                    $(this).closest('#oe_project_kanban_vignette').removeClass().addClass(self.kanban_color(1) + ' oe_project_kanban_vignette');
                    self.view.dataset.write(parseInt(this.id), {color:1},self.do_reload());
                });
                
                this.$element.find('.bgcolor_firebrick').click(function(){
                    $(this).closest('#oe_project_kanban_vignette').removeClass().addClass(self.kanban_color(2) + ' oe_project_kanban_vignette');
                    self.view.dataset.write(parseInt(this.id), {color:2},self.do_reload());
                    
                });
                
                this.$element.find('.bgcolor_khaki').click(function(){
                    $(this).closest('#oe_project_kanban_vignette').removeClass().addClass(self.kanban_color(3) + ' oe_project_kanban_vignette');
                    self.view.dataset.write(parseInt(this.id), {color:3},self.do_reload());
                    
                });
                
                this.$element.find('.bgcolor_thistle').click(function(){
                    $(this).closest('#oe_project_kanban_vignette').removeClass().addClass(self.kanban_color(4) + ' oe_project_kanban_vignette');
                    self.view.dataset.write(parseInt(this.id), {color:4},self.do_reload());
                    
                });
                
                this.$element.find('.bgcolor_orange').click(function(){
                    $(this).closest('#oe_project_kanban_vignette').removeClass().addClass(self.kanban_color(5) + ' oe_project_kanban_vignette');
                    self.view.dataset.write(parseInt(this.id), {color:5},self.do_reload());
                    
                });
                
            };
            self._super();
        }
    });
}
