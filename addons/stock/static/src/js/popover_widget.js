odoo.define('stock.popover_widget', function (require) {
    'use strict';

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const Context = require('web.Context');
    const data_manager = require('web.data_manager');
    const fieldRegistryOwl = require('web.field_registry_owl');

    class PopoverWidgetField extends AbstractFieldOwl {
        constructor() {
            super(...arguments);

            this.popoverTemplate = 'stock.popoverContent';
            this.placement = 'top';
            this.color = 'text-primary';
            this.icon = 'fa-info-circle';
            this.json_value = JSON.parse(this.value);
            if (this.json_value.trigger) {
                delete this.json_value.trigger;
            }
            Object.assign(this, this.json_value);
        }

        mounted() {
            // posted issue: https://github.com/odoo/owl/issues/710
            // can we have element without returning html else we can
            // put condition in Popover in xml itself, this is workaround
            // to hide element
            this.el.classList.toggle('d-none', !this.json_value);
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        get popoverTitle() {
            return this.json_value.title || this.title;
        }

        get popoverContentTemplate() {
            return this.json_value.popoverTemplate || this.popoverTemplate;
        }

        async _openForecast(ev) {
            const action = await data_manager.load_action('stock.report_stock_quantity_action_product');
            const additional_context = {
                grid_anchor: this.recordData.delivery_date_grid,
                search_default_warehouse_id: [this.recordData.warehouse_id.data.id],
                search_default_below_warehouse: false
            };
            action.context = new Context(action.context, additional_context);
            action.domain = [
                ['product_id', '=', this.recordData.product_id.data.id]
            ];
            return this.trigger('do-action', {action: action});
        }

    }

    PopoverWidgetField.supportedFieldTypes = ['char'];

    PopoverWidgetField.template = 'stock.popoverButton';

    fieldRegistryOwl.add('popover_widget', PopoverWidgetField);

    return PopoverWidgetField;

});
