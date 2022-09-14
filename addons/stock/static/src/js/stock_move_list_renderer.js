/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ViewButton } from "@web/views/view_button/view_button";

class MovesViewButton extends ViewButton {
    async onClick(ev) {
        if (this.props.clickParams.name != 'action_show_details') {
            super.onClick(ev)
        } else {
            await this.props.record.saveAndOpenActionShowDetails()
        }
    }
}
MovesViewButton.props = [...ViewButton.props]
export class MovesListRenderer extends ListRenderer {}

MovesListRenderer.recordRowTemplate = "stock.ListRenderer.RecordRow";
MovesListRenderer.components = { ...ListRenderer.components, ViewButton: MovesViewButton }

export class StockMoveX2ManyField extends X2ManyField {}
StockMoveX2ManyField.components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };

registry.category("fields").add("stock_move_one2many", StockMoveX2ManyField);
