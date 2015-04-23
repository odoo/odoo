odoo.define('hr_appraisal.hr_appraisal', function (require) {

var KanbanView = require('web_kanban.KanbanView');
var data = require('web.data');
var session = require('web.session');
    
KanbanView.include({
    appraisal_display_members_names: function() {
        /*
         * Set avatar title for managers.
         * In kanban views, many2many fields only return a list of ids.
         * We can implement return value of m2m fields like [(1,"Adminstration"),...].
         */
        var self = this;
        var manager_ids = [];

        // Collect manager ids
        self.$el.find('img[data-manager_ids]').each(function() {
            manager_ids.push($(this).data('manager_ids'));
        });

        // Find their matching names
        var dataset = new data.DataSetSearch(self, 'hr.employee', self.session.context, [['id', 'in', _.uniq(manager_ids)]]);
        dataset.read_slice(['id', 'name']).done(function(result) {
            _.each(result, function(v, k) {
                // Set the proper value in the DOM
                self.$el.find('img[data-manager_ids=' + v.id + ']').attr('title', v.name).tooltip();
            });
        });
    },
    on_groups_started: function() {
        var self = this;
        self._super.apply(self, arguments);
        if (self.dataset.model === 'hr.appraisal') {
            self.appraisal_display_members_names();
        }
    }
    });
});
