import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { TextField, ListTextField } from "@web/views/fields/text/text_field";
import { CharField } from "@web/views/fields/char/char_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useEffect } from "@odoo/owl";

export class SectionAndNoteListRenderer extends ListRenderer {
    static rowsTemplate = "account.sectionAndNoteListRenderer.Rows";
    static template = "account.sectionAndNoteListRenderer";

    /**
     * The purpose of this extension is to allow sections and notes in the one2many list
     * primarily used on Sales Orders and Invoices
     *
     * @override
     */
    setup() {
        super.setup();
        this.titleField = "name";
        this.sectionCols = ["print_details"];
        useEffect(
            (editedRecord) => this.focusToName(editedRecord),
            () => [this.editedRecord]
        )
    }

    focusToName(editRec) {
        if (editRec && editRec.isNew && this.isSectionOrNote(editRec)) {
            const col = this.columns.find((c) => c.name === this.titleField);
            this.focusCell(col, null);
        }
    }

    isSectionOrNote(record=null) {
        return this.isSection(record) || this.isNote(record);
    }

    isSection(record=null) {
        record = record || this.record;
        return record.data.display_type === 'line_section';
    }

    isNote(record=null) {
        record = record || this.record;
        return record.data.display_type === 'line_note';
    }

    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        return `${existingClasses} o_is_${record.data.display_type}`;
    }

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (
            (this.isSection(record) && !this.sectionCols.includes(column.name) || this.isNote(record))
            && column.widget !== "handle"
            && column.name !== this.titleField
        ) {
            return `${classNames} o_hidden`;
        }
        return classNames;
    }

    getActiveColumns() {
        return super.getActiveColumns().filter((col) => col.name !== "print_details" );
    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isSection(record)) {
            return this.getSectionColumns(super.getActiveColumns());
        } else if (this.isNote(record)) {
            return this.getNoteColumns(columns);
        }
        return columns;
    }

    getSectionColumns(columns) {
        const sectionCols = columns.filter(
            (col) =>
                col.widget === "handle"
                || (
                    col.type === "field"
                    && (col.name === this.titleField || this.sectionCols.includes(col.name))
                )
        );
        const hasProductRelatedColumn = ['product_id', 'product_template_id', 'name'].some(name =>
            this.columns.map(col => col.name).includes(name)
        );
        return sectionCols.map((col) => {
            if (
                col.name === this.titleField
                || (col.name === "print_details" && !hasProductRelatedColumn)
            ) {
                return {...col, colspan: this.columns.length - sectionCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }

    getNoteColumns(columns) {
        const noteCols = columns.filter((col) =>
            col.widget === "handle"
            || (col.type === "field" && col.name === this.titleField)
        );
        return noteCols.map((col) => {
            if (col.name === this.titleField) {
                return { ...col, colspan: columns.length - noteCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }
}

export class SectionAndNoteFieldOne2Many extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SectionAndNoteListRenderer,
    };
}

export class SectionAndNoteText extends Component {
    static template = "account.SectionAndNoteText";
    static props = { ...standardFieldProps };

    get componentToUse() {
        return this.props.record.data.display_type === 'line_section' ? CharField : TextField;
    }
}

export class ListSectionAndNoteText extends SectionAndNoteText {
    get componentToUse() {
        return this.props.record.data.display_type !== "line_section"
            ? ListTextField
            : super.componentToUse;
    }
}

export const sectionAndNoteFieldOne2Many = {
    ...x2ManyField,
    component: SectionAndNoteFieldOne2Many,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

export const sectionAndNoteText = {
    component: SectionAndNoteText,
    additionalClasses: ["o_field_text"],
};

export const listSectionAndNoteText = {
    ...sectionAndNoteText,
    component: ListSectionAndNoteText,
};

registry.category("fields").add("section_and_note_one2many", sectionAndNoteFieldOne2Many);
registry.category("fields").add("section_and_note_text", sectionAndNoteText);
registry.category("fields").add("list.section_and_note_text", listSectionAndNoteText);
