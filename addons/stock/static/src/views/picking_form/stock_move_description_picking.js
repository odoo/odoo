import { registry } from "@web/core/registry";
import { listTextField, ListTextField } from "@web/views/fields/text/text_field";

export class StockMoveDescriptionPicking extends ListTextField {
    get value() {
        const value = super.value;
        const productName = this.props.record.data.product_id.display_name;
        if (value === productName) {
            return "";
        }
        return value.trim();
    }
}

export const stockMoveDescriptionPickingField = {
    ...listTextField,
    component: StockMoveDescriptionPicking,
};

registry.category("fields").add("description_picking_text", listTextField);
registry.category("fields").add("list.description_picking_text", stockMoveDescriptionPickingField);
