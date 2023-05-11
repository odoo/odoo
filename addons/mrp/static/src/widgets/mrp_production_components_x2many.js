/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";

export class MrpProductionComponentsListRenderer extends ListRenderer {
    getCellClass(column, record) {
        let classNames = super.getCellClass(...arguments);
        if (column.name == "quantity_done" && !record.data.manual_consumption) {
            classNames += ' o_non_manual_consumption';
        }
        return classNames;
    }
}

export class MrpProductionComponentsX2ManyField extends X2ManyField {}
MrpProductionComponentsX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: MrpProductionComponentsListRenderer
};
MrpProductionComponentsX2ManyField.additionalClasses = ["o_field_many2many"];

export const mrpProductionComponentsX2ManyField = {
    ...x2ManyField,
    component: MrpProductionComponentsX2ManyField,
};

registry.category("fields").add("mrp_production_components_x2many", mrpProductionComponentsX2ManyField);
