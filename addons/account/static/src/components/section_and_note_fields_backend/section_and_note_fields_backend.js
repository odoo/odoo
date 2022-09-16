/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { TextField } from "@web/views/fields/text/text_field";
import { CharField } from "@web/views/fields/char/char_field";

const { Component, useEffect } = owl;

export class SectionAndNoteListRenderer extends ListRenderer {
    /**
     * The purpose of this extension is to allow sections and notes in the one2many list
     * primarily used on Sales Orders and Invoices
     *
     * @override
     */
    setup() {
        super.setup();
        this.titleField = "name";
        useEffect(
            () => this.focusToName(this.props.list.editedRecord),
            () => [this.props.list.editedRecord]
        )
    }

    focusToName(editRec) {
        if (editRec && editRec.isVirtual && this.isSectionOrNote(editRec)) {
            const col = this.state.columns.find((c) => c.name === this.titleField);
            this.focusCell(col, null);
        }
    }

    isSectionOrNote(record=null) {
        record = record || this.record;
        return ['line_section', 'line_note'].includes(record.data.display_type);
    }

    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        return `${existingClasses} o_is_${record.data.display_type}`;
    }

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (this.isSectionOrNote(record) && column.widget !== "handle" && column.name !== this.titleField) {
            return `${classNames} o_hidden`;
        }
        return classNames;
    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isSectionOrNote(record)) {
            return this.getSectionColumns(columns);
        }
        return columns;
    }

    getSectionColumns(columns) {
        const sectionCols = columns.filter((col) => col.widget === "handle" || col.type === "field" && col.name === this.titleField);
        return sectionCols.map((col) => {
            if (col.name === this.titleField) {
                return { ...col, colspan: columns.length - sectionCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }
}
SectionAndNoteListRenderer.template = "account.sectionAndNoteListRenderer";

export class SectionAndNoteFieldOne2Many extends X2ManyField {}
SectionAndNoteFieldOne2Many.components = {
    ...X2ManyField.components,
    ListRenderer: SectionAndNoteListRenderer,
};

export class SectionAndNoteText extends Component {
    get componentToUse() {
        return this.props.record.data.display_type === 'line_section' ? CharField : TextField;
    }
}
SectionAndNoteText.template = "account.SectionAndNoteText";

registry.category("fields").add("section_and_note_one2many", SectionAndNoteFieldOne2Many);
registry.category("fields").add("section_and_note_text", SectionAndNoteText);
