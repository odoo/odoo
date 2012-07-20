openerp.base_setup = function(openerp) {
    /* extend kanban to include the names of partner categories in the kanban view of partners */
    openerp.web_kanban.KanbanView.include({
        on_groups_started: function() {
            var self = this;
            self._super.apply(this, arguments);
            if (this.dataset.model === 'res.partner') {
                /* Set names for partner categories */
                var category_ids = [];
                this.$element.find('.oe_kanban_partner_categories span').each(function() {
                    category_ids.push($(this).data('category_id'));
                });
                var dataset = new openerp.web.DataSetSearch(this, 'res.partner.category',
                    self.session.context, [['id', 'in', _.uniq(category_ids)]]);
                dataset.read_slice(['id', 'name']).then(function(result) {
                    _.each(result, function(v, k) {
                        self.$element.find('.oe_kanban_partner_categories span[data-category_id=' + v.id + ']').html(v.name);
                    });
                });
            }
        }
    });
};
