/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { TextField } from "@web/views/fields/text/text_field";
import { CharField } from "@web/views/fields/char/char_field";

const { Component, xml } = owl;

export class SectionAndNoteListRenderer extends ListRenderer {
    /**
     * The purpose of this extension is to allow sections and notes in the one2many list
     * primarily used on Sales Orders and Invoices
     *
     * @override
     */
    setup() {
        super.setup();
        this.allowSectionsAndNotes = true;
    }

    getRowClass(record) {
        let classNames = super.getRowClass(record);
        classNames += record.data.display_type ? " o_is_" + record.data.display_type : ""
        return classNames;
    }

    getCellClass(column, record) {
        let classNames = super.getCellClass(column, record);
        const isSectionOrNote = record.data.display_type === 'line_section' || record.data.display_type === 'line_note';
        if (isSectionOrNote && column.widget !== "handle" && column.name !== "name") {
            classNames += " o_hidden";
        }
        return classNames;
    }

    getCellColspan(column, record) {
        const isSectionOrNote = record.data.display_type === 'line_section' || record.data.display_type === 'line_note';
        if (!isSectionOrNote || column.widget === "handle") {
            return 1;
        }
        let nbrColumns = this.withHandleColumn ? this.state.columns.length + 1 : this.state.columns.length;
        let withTrashColumn = this.props.activeActions && (this.props.activeActions.canDelete || this.props.activeActions.canUnlink || 0);
        return nbrColumns - this.withHandleColumn - withTrashColumn;
    }
}

export class SectionAndNoteFieldOne2Many extends X2ManyField {
    setup() {
        super.setup();
        if (this.viewMode === 'list') {
            this.Renderer = SectionAndNoteListRenderer;
        }
    }
}

export class SectionAndNoteText extends Component {
    get componentToUse() {
        return this.props.record.data.display_type === 'line_section' ? CharField : TextField;
    }
}
SectionAndNoteText.template = xml/* xml */ `
<t t-component="componentToUse" t-props="props"/>
`;

registry.category("fields").add("section_and_note_one2many", SectionAndNoteFieldOne2Many);
registry.category("fields").add("section_and_note_text", SectionAndNoteText);
