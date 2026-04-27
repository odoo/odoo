/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyBinaryField, many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";

export class Many2ManyBinaryFieldSignRequest extends Many2ManyBinaryField {
    static template = "sign.Many2ManyBinaryField";
}

export const many2ManyBinaryFieldSignRequest = {
    ...many2ManyBinaryField,
    component: Many2ManyBinaryFieldSignRequest,
};

registry.category("fields").add("many2many_binary_sign_request", many2ManyBinaryFieldSignRequest);
