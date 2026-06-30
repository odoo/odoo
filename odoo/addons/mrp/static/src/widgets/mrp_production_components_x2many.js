/** @odoo-module **/

import { registry } from "@web/core/registry";
import { StockMoveX2ManyField, stockMoveX2ManyField, MovesListRenderer } from "@stock/views/picking_form/stock_move_one2many";

export class MrpProductionComponentsListRenderer extends MovesListRenderer  {
    getCellClass(column, record) {
        let classNames = super.getCellClass(...arguments);
        if (column.name == "quantity" && !record.data.manual_consumption) {
            classNames += ' o_non_manual_consumption';
        }
        return classNames;
    }
}

export class MrpProductionComponentsX2ManyField extends StockMoveX2ManyField {}
MrpProductionComponentsX2ManyField.components = {
    ...StockMoveX2ManyField.components,
    ListRenderer: MrpProductionComponentsListRenderer,
};

export const mrpProductionComponentsX2ManyField = {
    ...stockMoveX2ManyField,
    component: MrpProductionComponentsX2ManyField,
    additionalClasses: [...StockMoveX2ManyField.additionalClasses || [], "o_field_many2many"],
};

registry.category("fields").add("mrp_production_components_x2many", mrpProductionComponentsX2ManyField);
