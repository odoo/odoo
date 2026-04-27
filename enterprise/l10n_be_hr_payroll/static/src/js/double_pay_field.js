/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class DoublePay2ManyField extends X2ManyField {
    get isMany2Many() {
        return false;
    }
}

export const doublePay2ManyField = {
    ...x2ManyField,
    component: DoublePay2ManyField,
};

registry.category("fields").add('double_pay', doublePay2ManyField);
