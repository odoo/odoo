/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class DataRecycleX2ManyField extends X2ManyField {
    static template = "data_recycle.DataRecycleX2ManyField";
}

export const dataRecycleX2ManyField = {
    ...x2ManyField,
    component: DataRecycleX2ManyField,
};

registry.category("fields").add("data_recycle_one2many", dataRecycleX2ManyField);
