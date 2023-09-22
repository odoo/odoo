/** @odoo-module **/

import { registry } from "@web/core/registry";
import { x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { StockMoveX2ManyField, MovesListRenderer } from "@stock/views/picking_form/stock_move_one2many";

export class MrpProductionComponentsListRenderer extends MovesListRenderer  {
    getCellClass(column, record) {
        let classNames = super.getCellClass(...arguments);
        if (column.name == "quantity_done" && !record.data.manual_consumption) {
            classNames += ' o_non_manual_consumption';
        }
        return classNames;
    }
}

export const mrpProductionComponentsX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField ,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_many2many"],
};

registry.category("fields").add("mrp_production_components_x2many", mrpProductionComponentsX2ManyField);
