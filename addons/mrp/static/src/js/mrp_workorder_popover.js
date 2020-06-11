odoo.define('mrp.mrp_workorder_popover', function (require) {
    'use strict';

    const PopoverWidget = require('stock.popover_widget');
    const fieldRegistryOwl = require('web.field_registry_owl');

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
    class MrpWorkorderPopover extends PopoverWidget {

        constructor() {
            super(...arguments);

            this.popoverTemplate = 'mrp.workorderPopover';
            this.title = this.env._t('Scheduling Information');
        }

        _onReplanClick(e) {
            this.rpc({
                model: 'mrp.workorder',
                method: 'action_replan',
                args: [[this.resId]]
            }).then(() => {
                this.trigger('reload');
            });
        }
    }

    fieldRegistryOwl.add('mrp_workorder_popover', MrpWorkorderPopover);

    return MrpWorkorderPopover;

});
