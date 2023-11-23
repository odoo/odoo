/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
<<<<<<< HEAD
import { useEffect } from "@odoo/owl";
||||||| parent of 42374376ce6b (temp)
import { ViewButton } from "@web/views/view_button/view_button";
=======
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ViewButton } from "@web/views/view_button/view_button";
>>>>>>> 42374376ce6b (temp)

export class MovesListRenderer extends ListRenderer {
    static recordRowTemplate = "stock.MovesListRenderer.RecordRow";

    setup() {
        super.setup();
        useEffect(
            () => {
                this.keepColumnWidths = false;
            },
            () => [this.state.columns]
        );
    }

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

<<<<<<< HEAD
MovesListRenderer.props = [ ...ListRenderer.props, 'stockMoveOpen?']

export class StockMoveX2ManyField extends X2ManyField {
    setup() {
        super.setup();
        this.canOpenRecord = true;
    }

    get isMany2Many() {
        return false;
    }



    async openRecord(record) {
        if (this.canOpenRecord) {
            const dirty = await record.isDirty();
            if (dirty && 'quantity' in record._changes) {
                await record.model.root.save({ reload: true });
            }
        }
        return super.openRecord(record);
    }
}
||||||| parent of 42374376ce6b (temp)
MoveViewButton.props = [...ViewButton.props];
export class MovesListRenderer extends ListRenderer {}

MovesListRenderer.components = { ...ListRenderer.components, ViewButton: MoveViewButton };
=======
MoveViewButton.props = [...ViewButton.props];
export class MovesListRenderer extends ListRenderer {}
MovesListRenderer.components = { ...ListRenderer.components, ViewButton: MoveViewButton };
>>>>>>> 42374376ce6b (temp)

<<<<<<< HEAD
StockMoveX2ManyField.components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
||||||| parent of 42374376ce6b (temp)
export class StockMoveX2ManyField extends X2ManyField {}
StockMoveX2ManyField.components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
=======
// Kanban view is displayed on mobile
export class MovesKanbanRecord extends KanbanRecord {}
MovesKanbanRecord.components = { ...KanbanRecord.components, ViewButton: MoveViewButton };

export class MovesKanbanRenderer extends KanbanRenderer {}
MovesKanbanRenderer.components = { ...KanbanRenderer.components, KanbanRecord: MovesKanbanRecord };

export class StockMoveX2ManyField extends X2ManyField {}
StockMoveX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: MovesListRenderer,
    KanbanRenderer: MovesKanbanRenderer
};
StockMoveX2ManyField.additionalClasses = ['o_field_one2many'];
>>>>>>> 42374376ce6b (temp)

export const stockMoveX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

registry.category("fields").add("stock_move_one2many", stockMoveX2ManyField);
