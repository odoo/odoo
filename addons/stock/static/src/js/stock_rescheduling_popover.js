odoo.define('stock.PopoverStockPicking', function (require) {
"use strict";

var core = require('web.core');

var PopoverWidgetField = require('stock.popover_widget');
var registry = require('web.field_registry');
var _lt = core._lt;

var PopoverStockPicking = PopoverWidgetField.extend({
    title: _lt('Planning Issue'),
    trigger: 'focus',
    color: 'text-danger',
    icon: 'fa-exclamation-triangle',

    _render: function () {
        this._super();
        if (this.$popover) {
            var self = this;
            this.$popover.find('a').on('click', function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: ev.currentTarget.getAttribute('element-model'),
                    res_id: parseInt(ev.currentTarget.getAttribute('element-id'), 10),
                    views: [[false, 'form']],
                    target: 'current'
                });
            });
        }
    },

});

registry.add('stock_rescheduling_popover', PopoverStockPicking);

return PopoverStockPicking;
});
