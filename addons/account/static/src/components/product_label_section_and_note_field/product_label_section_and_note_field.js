import { _t } from "@web/core/l10n/translation";
import { buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import { ProductNameAndDescriptionField } from "@product/product_name_and_description/product_name_and_description";

export class ProductLabelSectionAndNoteField extends ProductNameAndDescriptionField {
    static template = "account.ProductLabelSectionAndNoteField";

    setup() {
        super.setup();
        this.descriptionColumn = "name";
    }
}

export const productLabelSectionAndNoteField = {
    ...buildM2OFieldDescription(ProductLabelSectionAndNoteField),
    listViewWidth: [240, 400],
};
registry
    .category("fields")
    .add("product_label_section_and_note_field", productLabelSectionAndNoteField);
