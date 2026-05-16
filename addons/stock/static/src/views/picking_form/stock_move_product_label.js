import { registry } from "@web/core/registry";
import { ProductNameAndDescriptionField } from "@product/product_name_and_description/product_name_and_description";
import { many2OneField } from "@web/views/fields/many2one/many2one_field";

export class MoveProductLabelField extends ProductNameAndDescriptionField {
    static template = "stock.MoveProductLabelField";
    static descriptionColumn = "description_picking";

    get label() {
        const record = this.props.record.data;
        let label = record[this.descriptionColumn];
        const productName = record.product_id.display_name;
        if (label === productName) {
            label = "";
        }
        return label.trim();
    }
    get isDescriptionReadonly() {
        return this.props.readonly && ["done", "cancel"].includes(this.props.record.evalContext.parent.state);
    }
    get showLabelVisibilityToggler() {
        return !this.isDescriptionReadonly && this.columnIsProductAndLabel.value && !this.label;
    }
    parseLabel(value) {
        return value;
    }
}

export const moveProductLabelField = {
    ...many2OneField,
    component: MoveProductLabelField,
};
registry.category("fields").add("move_product_label_field", moveProductLabelField);
