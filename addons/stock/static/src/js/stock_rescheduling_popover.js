odoo.define('stock.PopoverStockPicking', function (require) {
    "use strict";

    const PopoverWidgetField = require('stock.popover_widget');
    const fieldRegistryOwl = require('web.field_registry_owl');

    class PopoverStockPicking extends PopoverWidgetField {

        constructor() {
            super(...arguments);

            this.title = this.env._t('Planning Issue');
            this.color = 'text-danger';
            this.icon = 'fa-exclamation-triangle';
        }

        _onClickElement(ev) {
            const action = {
                type: 'ir.actions.act_window',
                res_model: ev.currentTarget.getAttribute('element-model'),
                res_id: parseInt(ev.currentTarget.getAttribute('element-id'), 10),
                views: [[false, 'form']],
                target: 'current'
            };
            this.trigger('do-action', { action: action });
        }

    }

    fieldRegistryOwl.add('stock_rescheduling_popover', PopoverStockPicking);

    return PopoverStockPicking;

});
