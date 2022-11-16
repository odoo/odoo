odoo.define('sale.sales_team_dashboard', function (require) {
"use strict";

var core = require('web.core');
var KanbanRecord = require('web.KanbanRecord');
var session = require('web.session');
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
        var self = this;

        this.$target_input = $('<input>');
        this.$('.o_kanban_primary_bottom:last').html(this.$target_input);
        this.$target_input.focus();
        let preLabel = _t("Set an invoicing target: ");
        let postLabel = _t(" / Month");
        const kanbanBottomBlock = this.$el.find('.o_kanban_primary_bottom.bottom_block:last-child');
        if (this.recordData.currency_id) {
            const currency = session.get_currency(this.recordData.currency_id.res_id);
            if (currency.position === "after") {
                postLabel = ` ${' ' + currency.symbol}${postLabel}`;
            } else {
               preLabel = `${preLabel} ${currency.symbol + ' '}`;
            }
        }
        kanbanBottomBlock.prepend($('<span/>').text(preLabel));
        kanbanBottomBlock.append($('<span/>').text(postLabel));

        this.$target_input.on({
            blur: this._onSalesTeamTargetSet.bind(this),
            keydown: function (ev) {
                if (ev.keyCode === $.ui.keyCode.ENTER) {
                    self._onSalesTeamTargetSet();
                }
            },
        });
    },
    /**
     * Mostly a handler for what happens to the input "this.$target_input"
     *
     * @private
     *
     */
    _onSalesTeamTargetSet: function () {
        var self = this;
        var value = Number(this.$target_input.val());
        if (isNaN(value)) {
            this.displayNotification({ message: _t("Please enter an integer value"), type: 'danger' });
        } else {
            this.trigger_up('kanban_record_update', {
                invoiced_target: value,
                onSuccess: function () {
                    self.trigger_up('reload');
                },
            });
        }
    },
});

});
