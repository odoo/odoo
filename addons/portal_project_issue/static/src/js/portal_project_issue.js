openerp.portal_project_issue = function(openerp) {
    openerp.web_kanban.KanbanView.include({
        on_groups_started: function() {
            var self = this;
            self._super.apply(this, arguments);

            if (this.dataset.model === 'project.issue' || this.dataset.model === 'project.task') {
                /*
                 * Set proper names to project categories.
                 * In kanban views, many2many fields only return a list of ids.
                 * Therefore, we have to fetch the matching data by ourselves.
                 */
                var categ_ids = [];

                // Collect categories ids
                this.$element.find('.oe_form_field_many2manytags_box').each(function() {
                    categ_ids.push($(this).data('categ_id'));
                });

                // Find their matching names
                var dataset = new openerp.web.DataSetSearch(this, 'project.category', self.session.context, [['id', 'in', _.uniq(categ_ids)]]);
                dataset.read_slice(['id', 'name']).then(function(result) {
                    _.each(result, function(v, k) {
                        // Set the proper value in the DOM and display the element
                        self.$element.find('.oe_form_field_many2manytags_box[data-categ_id=' + v.id + ']').text(v.name).toggle();
                    });
                });
            }
        }
    });
};
