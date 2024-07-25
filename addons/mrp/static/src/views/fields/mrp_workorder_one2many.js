/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { AutoColumnWidthListRenderer } from "@stock/views/list/auto_column_width_list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class MrpWorkorderX2ManyField extends X2ManyField {
    static components = { ...X2ManyField.components, ListRenderer: AutoColumnWidthListRenderer };
}

export const mrpWorkorderX2ManyField = {
    ...x2ManyField,
    component: MrpWorkorderX2ManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

registry.category("fields").add("mrp_workorder_one2many", mrpWorkorderX2ManyField);

export const mrpWorkorderListView = {
    ...listView,
    Renderer: AutoColumnWidthListRenderer,
};

registry.category("views").add("mrp_workorder_list_view", mrpWorkorderListView);
