openerp.project = function(openerp) {
    openerp.web_kanban.KanbanView.include({
        on_groups_started: function() {
            var self = this;
            self._super.apply(this, arguments);
            if (this.dataset.model === 'project.project') {
                /* Set avatar title for members.
                   In many2many fields, returns only list of ids.
                   we can implement return value of m2m fields like [(1,"Adminstration"),...].
                */
                var members_ids = [];
                this.$element.find('.oe_kanban_project_avatars img').each(function() {
                    members_ids.push($(this).data('member_id'));
                });
                var dataset = new openerp.web.DataSetSearch(this, 'res.users', self.session.context, [['id', 'in', _.uniq(members_ids)]]);
                dataset.read_slice(['id', 'name']).then(function(result) {
                    _.each(result, function(v, k) {
                        self.$element.find('.oe_kanban_project_avatars img[data-member_id=' + v.id + ']').attr('title', v.name).tipsy({
                            offset: 10
                        });
                    });
                });
            }
        }
    });

    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function() {
            if (this.view.dataset.model === 'project.project') {
                this.$('.oe_kanban_project_list a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        }
    });
};
