/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ViewButton } from "@web/views/view_button/view_button";

class MoveViewButton extends ViewButton {
    async onClick(ev) {
        if (this.props.clickParams.name != "action_show_details") {
            super.onClick(ev);
        } else {
            await this.props.record.saveAndOpenDetails();
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

export class StockMoveX2ManyField extends X2ManyField {}
StockMoveX2ManyField.components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
StockMoveX2ManyField.additionalClasses = ['o_field_one2many'];

registry.category("fields").add("stock_move_one2many", StockMoveX2ManyField);
