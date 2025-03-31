/** @odoo-module **/

import { registry } from "@web/core/registry";
import { AutoColumnWidthListRenderer } from "@stock/views/list/auto_column_width_list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class MovesListRenderer extends AutoColumnWidthListRenderer {
    static recordRowTemplate = "stock.MovesListRenderer.RecordRow";

    processAllColumn(allColumns, list) {
        let cols = super.processAllColumn(...arguments);
        if (list.resModel === "stock.move") {
            cols.push({
                type: 'opendetailsop',
                id: `column_detailOp_${cols.length}`,
                column_invisible: 'parent.state=="draft"',
            });
        }
        return cols;
    }
}

export class StockMoveX2ManyField extends X2ManyField {
    static components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
    setup() {
        super.setup();
        this.canOpenRecord = true;
    }

    get isMany2Many() {
        return false;
    }

    async openRecord(record) {
        if (this.canOpenRecord && !record.isNew) {
            const dirty = await record.isDirty();
            if (await record._parentRecord.isDirty() || (dirty && 'quantity' in record._changes)) {
                await record._parentRecord.save({ reload: true });
                record = record._parentRecord.data[this.props.name].records.find(e => e.resId === record.resId);
                if (!record) {
                    return;
                }
            }
        }
        return super.openRecord(record);
    }
}


export const stockMoveX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

registry.category("fields").add("stock_move_one2many", stockMoveX2ManyField);
