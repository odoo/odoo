/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
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
MrpProductionComponentsX2ManyField.components = { ...X2ManyField.components, ListRenderer: MrpProductionComponentsListRenderer };

registry.category("fields").add("mrp_production_components_x2many", MrpProductionComponentsX2ManyField);
