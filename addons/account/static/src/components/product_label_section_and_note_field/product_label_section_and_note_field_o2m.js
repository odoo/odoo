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
        const productCol = activeColumns.find((col) => this.productColumns.includes(col.name));
        const hasDescriptionCol = activeColumns.some((col) => col.name === this.descriptionColumn);

        if (productCol) {
            activeColumns = activeColumns.filter(
                (col) => ![this.labelColumn, this.descriptionColumn].includes(col.name)
            );
            this.titleField = productCol.name;
        } else if (hasDescriptionCol) {
            activeColumns = activeColumns.filter((col) => col.name !== this.descriptionColumn);
            this.titleField = this.labelColumn;
        } else {
            activeColumns = activeColumns.filter((col) => col.name !== this.labelColumn);
        }

        const columnIsProductAndLabel = !!productCol && hasDescriptionCol;
        this.props.list.records.forEach((record) => {
            record.columnIsProductAndLabel = columnIsProductAndLabel;
        });

        return activeColumns;
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
