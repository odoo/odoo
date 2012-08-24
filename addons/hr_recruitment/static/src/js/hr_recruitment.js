openerp.hr_recruitment = function(openerp) {
    openerp.web_kanban.KanbanView.include({
        applicant_display_categ_names: function() {
            /*
             * Set proper names to applicant categories.
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
            var dataset = new openerp.web.DataSetSearch(self, 'hr.applicant_category', self.session.context, [['id', 'in', _.uniq(categ_ids)]]);
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

            if (self.dataset.model === 'hr.applicant') {
                self.applicant_display_categ_names();
            }
        }
    });
};
