odoo.define('sale.sales_team_dashboard', function (require) {
"use strict";

var core = require('web.core');
var KanbanRecord = require('web_kanban.Record');
var Model = require('web.Model');
var _t = core._t;

KanbanRecord.include({
    events: _.defaults({
        'click .sales_team_target_definition': 'on_sales_team_target_click',
    }, KanbanRecord.prototype.events),

    on_sales_team_target_click: function(ev) {
        ev.preventDefault();

        this.$target_input = $('<input>');
        this.$('.o_kanban_primary_bottom').html(this.$target_input);
        this.$('.o_kanban_primary_bottom').prepend(_t("Set an invoicing target: "));
        this.$target_input.focus();

        var self = this;
        this.$target_input.blur(function() {
            var value = Number(self.$target_input.val());
            if (isNaN(value)) {
                self.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
            } else {
                new Model('crm.team').call('write', [[self.id], { 'invoiced_target': value }]).done(function() {
                    self.trigger_up('kanban_record_update', {id: self.id});
                });
            }
        });
    },
});

});
