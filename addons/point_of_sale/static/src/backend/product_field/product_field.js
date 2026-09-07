import {
    ProductLabelSectionAndNoteField,
    productLabelSectionAndNoteField,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";
import { registry } from "@web/core/registry";

export class PosOrderLineProductField extends ProductLabelSectionAndNoteField {
    static descriptionColumn = "custom_attribute_value_ids";

    get label() {
        return this.props.record.data[this.descriptionColumn]
            ? this.props.record.data[this.descriptionColumn].records
                  .map((r) => r.data.display_name)
                  .join("")
            : "";
    }
}

export const posOrderLineProductField = {
    ...productLabelSectionAndNoteField,
    component: PosOrderLineProductField,
};

registry.category("fields").add("pos_product_many2one", posOrderLineProductField);
