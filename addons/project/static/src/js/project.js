openerp.project = function(openerp) {
    openerp.web_kanban.ProjectKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            var self = this;
            self._super();
            if (this.view.dataset.model == 'project.project') {
                /*set avatar title for members.
                In many2many fields, returns only list of ids.
                we can implement return value of m2m fields like [(1,"Adminstration"),...].
                */
                _.each($(this.$element).find('.project_avatar'), function(avatar) {
                    var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, [['id','=',avatar.id]]);
                    dataset.read_slice(['name']).then(function(result) {
                        avatar.setAttribute("title",result[0].name);
                    });
                });

                // set sequence like Tasks,Issues,Timesheets and Phases
                var my_list = $("#list a");
                my_list.sort(function (a, b) {
                    var aValue = parseInt(a.id, 10);
                    var bValue = parseInt(b.id, 10);
                    return aValue == bValue ? 0 : aValue < bValue ? -1 : 1;
                });
                $('#list').replaceWith(my_list);

                // when vignette is clicked, it opens the first action in sequence
                if (my_list.length !== 0) {
                    var click_button = $(this.$element).find('.click_button');
                    click_button.attr('data-name', my_list[0].getAttribute('data-name'));
                    click_button.attr('data-type', "action");
                }

                /* set background color.
                  we can do other way to implement new widget.
                  because we need to rpc call for that.
                */
                this.$element.find('.bgcolor').click(function() {
                    var color = parseInt($(this).find('span').attr('class').split(' ')[0].substring(16), 10);
                    var color_class = $(this).find('span').attr('class').split(' ')[0];
                    $(this).closest('#oe_project_kanban_vignette').removeClass().addClass(color_class + ' oe_project_kanban_vignette');
                    self.view.dataset.write(parseInt(this.id, 10), {color:color});
                });
            }
        }
    });
};
