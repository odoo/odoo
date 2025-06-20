import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { TextField, ListTextField } from "@web/views/fields/text/text_field";
import { CharField } from "@web/views/fields/char/char_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useEffect, useSubEnv } from "@odoo/owl";
import { x2ManyCommands } from "@web/core/orm_service";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

function findSectionTargetRecord(records, currentIndex, direction, isDisplayType) {
    if(direction == 'up') {
        let prevSectionIndex = -1;

        for (let i=currentIndex-1; i>=0; i--) {
            if (isDisplayType(records[i])) {
                prevSectionIndex = i;
                break;
            }
        }
        if(prevSectionIndex == -1) return null;

        return records[prevSectionIndex -1]; // For moving up we expect the line before previous header
    }

    if(direction == 'down') {
        let nextSectionIndex = -1;

        for (let i=currentIndex+1; i<records.length; i++) {
            if (isDisplayType(records[i])) {
                nextSectionIndex = i;
                break;
            }
        }
        if(nextSectionIndex == -1) return null;

        return records[nextSectionIndex]; // For moving down we expect the line of header
    }
}

export class SectionAndNoteListRenderer extends ListRenderer {
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
        this.sectionCols = ['section_settings'];
        this.dialogService = useService('dialog');

        useEffect(
            (editedRecord) => this.focusToName(editedRecord),
            () => [this.editedRecord]
        )
        useSubEnv({
            onSectionDelete: async (sectionId) => await this.onSectionDelete(sectionId),
            onSectionDuplicate: async (record) => await this.onSectionDuplicate(record),
            onSectionMoveUp: async (record) => await this.onSectionMoveUp(record),
            onSectionMoveDown: async (record) => await this.onSectionMoveDown(record),
        });
    }

    focusToName(editRec) {
        if (editRec && editRec.isNew && this.isSectionOrNote(editRec)) {
            const col = this.columns.find((c) => c.name === this.titleField);
            this.focusCell(col, null);
        }
    }

    isSectionOrNote(record = null) {
        return this.isSection(record) || this.isNote(record);
    }

    isSection(record = null) {
        record = record || this.record;
        return ['line_subsection', 'line_section'].includes(record.data.display_type);
    }

    isNote(record = null) {
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
                || (col.name === this.titleField || this.sectionCols.includes(col.name))
        );
        return sectionCols.map((col) => {
            if (col.name === this.titleField) {
                return { ...col, colspan: this.columns.length - sectionCols.length + 1 };
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

    getSectionBlock(sectionLine) {
        const childSubsectionsId = this.props.list.records.filter(
            (r) => r.data.linked_section_line_id.id === sectionLine.resId
                && r.data.display_type == 'line_subsection'
        );

        const childLinesId = this.props.list.records.filter(
            (r) => [...childSubsectionsId.map((r) => r.resId), sectionLine.resId].includes(
                r.data.linked_section_line_id.id
            )
                && r.data.display_type != 'line_subsection'
        );

        return [sectionLine, ...childSubsectionsId, ...childLinesId];
    }

    async onSectionDelete(sectionLine) {
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Delete Section?"),
            body: _t("Are you sure you want to delete this section and all its components?"),
            confirm: async () => {
                await this.props.list._applyCommands(
                    this.getSectionBlock(sectionLine).map((r) => r.resId).map(
                        (id) => [x2ManyCommands.DELETE, id]
                    )
                );
                await this.props.list._onUpdate();
            },
            cancel: () => { },
            confirmLabel: _t("Delete"),
            cancelLabel: _t("Cancel"),
        });
    }

    async onSectionDuplicate(sectionLine) {
        await this.props.list._applyCommands(
            this.getSectionBlock(sectionLine).map(
                (record) => [x2ManyCommands.CREATE, false, {
                    display_type: record.data.display_type,
                    product_id: { id: record.data.product_id.id },
                    quantity: record.data.quantity,
                    name: record.data.name,
                    currency_id: { id: record.data.currency_id.id },
                }]
            )
        );
        await this.props.list._onUpdate();
    }

    async onSectionMoveUp(sectionLine) {
        const isDisplayType = (r) => r.data.display_type === sectionLine.data.display_type;
        const targetLine = findSectionTargetRecord(
            this.props.list.records,
            this.props.list.records.findIndex((r) => r.id === sectionLine.id),
            'up',
            isDisplayType
        );

        if (!targetLine) {
            return;
        }

        await this.props.list._resequenceMultiple(
            this.getSectionBlock(sectionLine).map((r) => r.id),
            targetLine.id
        )
    }

    async onSectionMoveDown(sectionLine) {
        const isDisplayType = (r) => r.data.display_type === sectionLine.data.display_type;
        const sectionBlock = this.getSectionBlock(sectionLine);
        const targetLine = findSectionTargetRecord(
            this.props.list.records,
            this.props.list.records.findIndex((r) => r.id === sectionBlock[sectionBlock.length - 1].id),
            'down',
            isDisplayType
        );

        if (!targetLine) {
            return;
        }

        await this.props.list._resequenceMultiple(
            this.getSectionBlock(sectionLine).map((r) => r.id),
            targetLine.id
        )
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
        return ['line_section', 'line_subsection'].includes(this.props.record.data.display_type) ? CharField : TextField;
    }
}

export class ListSectionAndNoteText extends SectionAndNoteText {
    get componentToUse() {
        return !['line_section', 'line_subsection'].includes(this.props.record.data.display_type)
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
