import {
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
    SectionAndNoteListRenderer,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { registry } from "@web/core/registry";

export class ProductLabelSectionAndNoteListRender extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
        this.descriptionColumn = "name";
        this.labelColumn = "label";
        // product_template_id is added for purchase_product_matrix's PO view and sale's SO view
        this.productColumns = ["product_id", "product_template_id"];
    }

    isCellReadonly(column, record) {
        if (![...this.productColumns, "name"].includes(column.name)) {
            return super.isCellReadonly(column, record);
        }
        // The isCellReadonly method from the ListRenderer is used to determine the classes to apply to the cell.
        // We need this override to make sure some readonly classes are not applied to the cell if it is still editable.
        const isReadonly = super.isCellReadonly(column, record);
        return (
            isReadonly
            && (["cancel", "posted"].includes(record.evalContext.parent.state)
            || record.evalContext.parent.locked)
        )
    }

    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        const productColActive = this.optionalActiveFields["product_id"];
        const descriptionFieldActive = this.optionalActiveFields["name"];

        // Hide the stacked product_and_description column if neither the product nor the
        // description field is active.
        if (!productColActive && !descriptionFieldActive) {
            activeColumns = activeColumns.filter((col) => col.name != "product_and_description");
        }

        return activeColumns;
    }

    isColumnGroupFieldVisible(fieldInfo, record) {
        // Always show name field for section and note.
        if (this.isSectionOrNote(record)) {
            return fieldInfo.name === "name";
        }

        if (!super.isColumnGroupFieldVisible(fieldInfo, record)) {
            return false;
        }

        const isProductFieldActive = this.optionalActiveFields["product_id"];

        if (fieldInfo.name === "label") {
            return !isProductFieldActive;
        }
        if (fieldInfo.name === "name") {
            return isProductFieldActive;
        }
        return true;
    }
}

export class ProductLabelSectionAndNoteOne2Many extends SectionAndNoteFieldOne2Many {
    static components = {
        ...super.components,
        ListRenderer: ProductLabelSectionAndNoteListRender,
    };
}

export const productLabelSectionAndNoteOne2Many = {
    ...sectionAndNoteFieldOne2Many,
    component: ProductLabelSectionAndNoteOne2Many,
};

registry
    .category("fields")
    .add("product_label_section_and_note_field_o2m", productLabelSectionAndNoteOne2Many);
