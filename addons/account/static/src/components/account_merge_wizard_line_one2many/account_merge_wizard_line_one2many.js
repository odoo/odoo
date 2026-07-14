/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    SectionAndNoteListRenderer,
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
} from "../section_and_note_fields_backend/section_and_note_fields_backend";

export class AccountMergeWizardLinesRenderer extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
        this.titleField = "info";
    }

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        // Even though the `is_selected` field is invisible for section lines, we should
        // keep its column (which would be hidden by the call to super.getCellClass)
        // in order to align the section header name with the account names.
        if (this.isSectionOrNote(record) && column.name === "is_selected") {
            return classNames.replace(" o_hidden", "");
        }
        return classNames;
    }

    /** @override **/
    getSectionColumns(columns) {
        const sectionCols = columns.filter(
            (col) =>
                col.type === "field" && (col.name === this.titleField || col.name === "is_selected")
        );
        return sectionCols.map((col) => {
            if (col.name === this.titleField) {
                return { ...col, colspan: columns.length - sectionCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }

    /** @override */
    isSortable(column) {
        // Don't allow sorting columns, as that doesn't make sense in the wizard view.
        return false;
    }
}

export class AccountMergeWizardLinesOne2Many extends SectionAndNoteFieldOne2Many {
    static components = {
        ...SectionAndNoteFieldOne2Many.components,
        ListRenderer: AccountMergeWizardLinesRenderer,
    };
}

export const accountMergeWizardLinesOne2Many = {
    ...sectionAndNoteFieldOne2Many,
    component: AccountMergeWizardLinesOne2Many,
};

registry
    .category("fields")
    .add("account_merge_wizard_lines_one2many", accountMergeWizardLinesOne2Many);
