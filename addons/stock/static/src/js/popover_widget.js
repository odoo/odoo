odoo.define('stock.popover_widget', function (require) {
    'use strict';

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const fieldRegistryOwl = require('web.field_registry_owl');

    class PopoverWidgetField extends AbstractFieldOwl {
        constructor() {
            super(...arguments);

            this.popoverTemplate = 'stock.popoverContent';
            this.placement = 'top';
            this.color = 'text-primary';
            this.icon = 'fa-info-circle';
            this.json_value = JSON.parse(this.value);
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

    }

    PopoverWidgetField.supportedFieldTypes = ['char'];

    PopoverWidgetField.template = 'stock.popoverButton';

    fieldRegistryOwl.add('popover_widget', PopoverWidgetField);

    return PopoverWidgetField;

});
