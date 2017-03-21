odoo.define('sale.sales_team_dashboard', function (require) {
"use strict";

var core = require('web.core');
var KanbanRecord = require('web.KanbanRecord');
var _t = core._t;

KanbanRecord.include({
    events: _.defaults({
        'click .sales_team_target_definition': '_onSalesTeamTargetClick',
    }, KanbanRecord.prototype.events),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {MouseEvent} ev
     */
    _onSalesTeamTargetClick: function (ev) {
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
                self._rpc('crm.team', 'write')
                    .args([[self.id], { 'invoiced_target': value }])
                    .exec()
                    .done(function() {
                        self.trigger_up('kanban_record_update', {id: self.id});
                    });
            }
        });
    },
});

});
