openerp.project = function(openerp) {
    openerp.web_kanban.KanbanView.include({
        project_display_members_names: function() {
            /*
             * Set avatar title for members.
             * In kanban views, many2many fields only return a list of ids.
             * We can implement return value of m2m fields like [(1,"Adminstration"),...].
             */
            var self = this;
            var members_ids = [];

            // Collect members ids
            self.$element.find('img[data-member_id]').each(function() {
                members_ids.push($(this).data('member_id'));
            });

            // Find their matching names
            var dataset = new openerp.web.DataSetSearch(self, 'res.users', self.session.context, [['id', 'in', _.uniq(members_ids)]]);
            dataset.read_slice(['id', 'name']).then(function(result) {
                _.each(result, function(v, k) {
                    // Set the proper value in the DOM
                    self.$element.find('img[data-member_id=' + v.id + ']').attr('title', v.name).tipsy({
                        offset: 10
                    });
                });
            });
        },
        project_display_categ_names: function() {
            /*
             * Set proper names to project categories.
             * In kanban views, many2many fields only return a list of ids.
             * Therefore, we have to fetch the matching data by ourselves.
             */
            var self = this;
            var categ_ids = [];

            // Collect categories ids
            self.$element.find('span[data-categ_id]').each(function() {
                categ_ids.push($(this).data('categ_id'));
            });

            // Find their matching names
            var dataset = new openerp.web.DataSetSearch(self, 'project.category', self.session.context, [['id', 'in', _.uniq(categ_ids)]]);
            dataset.read_slice(['id', 'name']).then(function(result) {
                _.each(result, function(v, k) {
                    // Set the proper value in the DOM and display the element
                    self.$element.find('span[data-categ_id=' + v.id + ']').text(v.name);
                });
            });
        },
        on_groups_started: function() {
            var self = this;
            self._super.apply(self, arguments);

            if (self.dataset.model === 'project.project') {
                self.project_display_members_names();
            } else if (self.dataset.model === 'project.task') {
                self.project_display_categ_names();
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
