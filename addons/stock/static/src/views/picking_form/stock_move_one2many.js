/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class MovesListRenderer extends ListRenderer {
    processAllColumn(allColumns, list) {
        let cols = super.processAllColumn(...arguments);
        if (list.resModel === "stock.move") {
            cols.push({
                type: 'opendetailsop',
                id: `column_detailOp_${cols.length}`,
            });
        }
        return cols;
    }
}

MovesListRenderer.props = [ ...ListRenderer.props, 'stockMoveOpen?']

export class StockMoveX2ManyField extends X2ManyField {
    setup() {
        super.setup();
        this.canOpenRecord = true;
    }

    get isMany2Many() {
        return false;
    }
}

StockMoveX2ManyField.components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };

export const stockMoveX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

registry.category("fields").add("stock_move_one2many", stockMoveX2ManyField);
