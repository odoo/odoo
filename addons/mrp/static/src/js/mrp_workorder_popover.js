odoo.define('mrp.mrp_workorder_popover', function (require) {
'use strict';

var PopoverWidget = require('stock.popover_widget');
var fieldRegistry = require('web.field_registry');
var core = require('web.core');
var _t = core._t;


/**
 * Link to a Char field representing a JSON:
 * {
 *  'replan': <REPLAN_BOOL>, // Show the replan btn
 *  'color': '<COLOR_CLASS>', // Color Class of the icon (d-none to hide)
 *  'infos': [
 *      {'msg' : '<MESSAGE>', 'color' : '<COLOR_CLASS>'},
 *      {'msg' : '<MESSAGE>', 'color' : '<COLOR_CLASS>'},
 *      ... ]
 * }
 */
var MrpWorkorderPopover = PopoverWidget.extend({
    popoverTemplate: 'mrp.workorderPopover',
    title: _t('Scheduling Information'),

    _render: function () {
        this._super.apply(this, arguments);
        if (! this.$popover) {
          return;
        }
        var self = this;
        this.$popover.find('.action_replan_button').click(function (e) {
            self._onReplanClick(e);
        });
    },

    _onReplanClick:function (e) {
        var self = this;
        this._rpc({
            model: 'mrp.workorder',
            method: 'action_replan',
            args: [[self.res_id]]
        }).then(function () {
            self.trigger_up('reload');
        });
    },
});

fieldRegistry.add('mrp_workorder_popover', MrpWorkorderPopover);

return MrpWorkorderPopover;
});
