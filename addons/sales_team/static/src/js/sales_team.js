odoo.define('sales_team.update_kanban', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var KanbanRecord = require('web.KanbanRecord');
var data = require('web.data');
var session = require('web.session');

KanbanView.include({
    crm_display_members_names: function() {
        /*
         * Set avatar title for members.
         * In kanban views, many2many fields only return a list of ids.
         * We can implement return value of m2m fields like [(1,"Adminstration"),...].
         */
        var self = this;
        var members_ids = [];

        // Collect members ids
        self.$el.find('img[data-member_id]').each(function() {
            members_ids.push($(this).data('member_id'));
        });

        // Find their matching names
        var dataset = new data.DataSetSearch(self, 'res.users', session.context, [['id', 'in', _.uniq(members_ids)]]);
        dataset.read_slice(['id', 'name']).done(function(result) {
            _.each(result, function(v) {
                // Set the proper value in the DOM
                self.$el.find('img[data-member_id=' + v.id + ']').attr('title', v.name).tooltip();
            });
        });
    },
    on_groups_started: function() {
        var self = this;
        self._super.apply(self, arguments);

        if (self.dataset.model === 'crm.team') {
            self.crm_display_members_names();
        }
    },
});

KanbanRecord.include({
    on_card_clicked: function() {
        if (this.model === 'crm.team') {
            this.$('.oe_kanban_crm_salesteams_list a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
