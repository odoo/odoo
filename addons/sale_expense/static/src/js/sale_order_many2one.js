/** @odoo-module **/

import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';

import { registry } from "@web/core/registry";

export class OrderField extends Many2OneField {
    setup() {
        super.setup();
    }

    /**
     * @override
     */
    get Many2XAutocompleteProps() {
        // hide the search more option from the dropdown menu
       return {
           ...super.Many2XAutocompleteProps,
           noSearchMore: true,
       }
    }
}

export const orderField = {
    ...many2OneField,
    component: OrderField,
};

registry.category("fields").add("sale_order_many2one", orderField);
registry.add('sale_order_many2one', OrderField);
