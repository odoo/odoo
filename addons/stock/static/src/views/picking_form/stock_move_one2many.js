/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ViewButton } from "@web/views/view_button/view_button";

class MoveViewButton extends ViewButton {
    async onClick(ev) {
        if (this.env.model.root.resModel == "stock.picking" && this.props.clickParams.name == "action_show_details") {
            await this.props.record.saveAndOpenDetails();
        } else {
            super.onClick(ev);
        }
    }

    get disabled() {
        if (this.props.clickParams.name == "action_show_details") {
            return false;
        }
        return super.disabled;
    }
}

MoveViewButton.props = [...ViewButton.props];
export class MovesListRenderer extends ListRenderer {}
MovesListRenderer.components = { ...ListRenderer.components, ViewButton: MoveViewButton };

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

registry.category("fields").add("stock_move_one2many", StockMoveX2ManyField);
