import {
    SectionAndNoteListRenderer,
    sectionAndNoteFieldOne2Many,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class ProductLabelSectionAndNoteListRender extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
        this.productColumns = ["product_id", "product_template_id"];
    }

    getCellTitle(column, record) {
        // When using this list renderer, we don't want the product_id cell to have a tooltip with its label.
        if (this.productColumns.includes(column.name)) {
            return;
        }
        super.getCellTitle(column, record);
    }

    getActiveColumns(list) {
        let activeColumns = super.getActiveColumns(list);
        const productCol = activeColumns.find((col) => this.productColumns.includes(col.name));
        const labelCol = activeColumns.find((col) => col.name === "name");

        if (productCol) {
            if (labelCol) {
                list.records.forEach((record) => (record.columnIsProductAndLabel = true));
            } else {
                list.records.forEach((record) => (record.columnIsProductAndLabel = false));
            }
            activeColumns = activeColumns.filter((col) => col.name !== "name");
            this.titleField = productCol.name;
        } else {
            this.titleField = "name";
        }

        return activeColumns;
    }
}

export class ProductLabelSectionAndNoteOne2Many extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: ProductLabelSectionAndNoteListRender,
    };
}

export const productLabelSectionAndNoteOne2Many = {
    ...x2ManyField,
    component: ProductLabelSectionAndNoteOne2Many,
    additionalClasses: sectionAndNoteFieldOne2Many.additionalClasses,
};

registry
    .category("fields")
    .add("product_label_section_and_note_field_o2m", productLabelSectionAndNoteOne2Many);
