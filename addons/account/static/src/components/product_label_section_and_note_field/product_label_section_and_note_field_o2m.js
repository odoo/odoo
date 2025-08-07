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

    processAllColumn(allColumns, list) {
        allColumns = allColumns.map((column) => {
            if (column["optional"] === "conditional" && column["name"] === "product_id") {
                /**
                 * The preference should be different for Bills & Invoices lines
                 * Invoices -> Should show the products by default
                 * Bills -> Should show the labels by default
                 */
                column["optional"] = ["in_invoice", "in_refund", "in_receipt"].includes(
                    this.props.list.evalContext.parent.move_type
                )
                    ? "hide"
                    : "show";
            }
            return column;
        });
        return super.processAllColumn(allColumns, list);
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

    isCellReadonly(column, record) {
        if (![...this.productColumns, "name"].includes(column.name)) {
            return super.isCellReadonly(column, record);
        }
        // The isCellReadonly method from the ListRenderer is used to determine the classes to apply to the cell.
        // We need this override to make sure some readonly classes are not applied to the cell if it is still editable.
        let isReadonly = super.isCellReadonly(column, record);
        return (
            isReadonly
            && (["cancel", "posted"].includes(record.evalContext.parent.state)
            || record.evalContext.parent.locked)
        )
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
