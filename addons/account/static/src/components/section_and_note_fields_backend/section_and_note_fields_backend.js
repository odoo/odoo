import { Component, useEffect } from "@odoo/owl";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ListTextField, TextField } from "@web/views/fields/text/text_field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";

const DISPLAY_TYPES = {
    NOTE: "line_note",
    SECTION: "line_section",
    SUBSECTION: "line_subsection",
};

function getPreviousSectionRecords(list, record) {
    const { sectionRecords } = getRecordsUntilSection(list, record, false);
    return sectionRecords;
}

function getSectionRecords(list, record, subSection) {
    const { sectionRecords } = getRecordsUntilSection(list, record, true, subSection);
    return sectionRecords;
}

function hasNextSection(list, record) {
    const { indexAtEnd } = getRecordsUntilSection(list, record, true);
    return indexAtEnd < list.records.length && list.records[indexAtEnd].data.display_type === record.data.display_type;
}

function hasPreviousSection(list, record) {
    const { indexAtEnd } = getRecordsUntilSection(list, record, false);
    return indexAtEnd >= 0 && list.records[indexAtEnd].data.display_type === record.data.display_type;
}

function getRecordsUntilSection(list, record, asc, subSection) {
    const stopAtTypes = [DISPLAY_TYPES.SECTION];
    if (subSection ?? record.data.display_type === DISPLAY_TYPES.SUBSECTION) {
        stopAtTypes.push(DISPLAY_TYPES.SUBSECTION);
    }

    const sectionRecords = [];
    let index = list.records.indexOf(record);
    if (asc) {
        sectionRecords.push(list.records[index]);
        index++;
        while (index < list.records.length && !stopAtTypes.includes(list.records[index].data.display_type)) {
            sectionRecords.push(list.records[index]);
            index++;
        }
    } else {
        index--;
        while (index >= 0 && !stopAtTypes.includes(list.records[index].data.display_type)) {
            sectionRecords.unshift(list.records[index]);
            index--;
        }
        sectionRecords.unshift(list.records[index]);
    }

    return {
        sectionRecords,
        indexAtEnd: index,
    };
}

export class SectionAndNoteListRenderer extends ListRenderer {
    static template = "account.SectionAndNoteListRenderer";
    static recordRowTemplate = "account.SectionAndNoteListRenderer.RecordRow";

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
            (editedRecord) => this.focusToName(editedRecord),
            () => [this.editedRecord]
        );
    }

    async addRowAfterSection(record, addSubSection) {
        const canProceed = await this.props.list.leaveEditMode();
        if (!canProceed) {
            return;
        }

        const index =
            this.props.list.records.indexOf(record) +
            getSectionRecords(this.props.list, record).length -
            1;
        const context = {
            default_display_type: addSubSection ? DISPLAY_TYPES.SUBSECTION : DISPLAY_TYPES.SECTION,
        };
        await this.props.list.addNewRecordAtIndex(index, { context });
    }

    async addNoteInSection(record) {
        const canProceed = await this.props.list.leaveEditMode();
        if (!canProceed) {
            return;
        }

        const index =
            this.props.list.records.indexOf(record) +
            getSectionRecords(this.props.list, record, true).length -
            1;
        const context = {
            default_display_type: DISPLAY_TYPES.NOTE,
        };
        await this.props.list.addNewRecordAtIndex(index, { context });
    }

    async addRowInSection(record, addSubSection) {
        const canProceed = await this.props.list.leaveEditMode();
        if (!canProceed) {
            return;
        }

        const index =
            this.props.list.records.indexOf(record) +
            getSectionRecords(this.props.list, record, !addSubSection).length -
            1;
        const context = {};
        if (addSubSection) {
            context["default_display_type"] = DISPLAY_TYPES.SUBSECTION;
        }
        await this.props.list.addNewRecordAtIndex(index, { context });
    }

    canAddSubSection() {
        const selection = new Map(this.props.list.fields.display_type.selection);
        return selection.has(DISPLAY_TYPES.SUBSECTION);
    }

    async deleteSection(record) {
        if (this.editedRecord && this.editedRecord !== record) {
            const left = await this.props.list.leaveEditMode();
            if (!left) {
                return;
            }
        }
        if (this.activeActions.onDelete) {
            const method = this.activeActions.unlink ? "unlink" : "delete";
            const commands = [];
            const sectionRecords = getSectionRecords(this.props.list, record);
            for (const sectionRecord of sectionRecords) {
                commands.push(
                    x2ManyCommands[method](sectionRecord.resId || sectionRecord._virtualId)
                );
            }
            await this.props.list.applyCommands(commands);
        }
    }

    async duplicateSection(record) {
        const left = await this.props.list.leaveEditMode();
        if (!left) {
            return;
        }

        const sectionRecords = getSectionRecords(this.props.list, record);
        await this.props.list.duplicateRecords(sectionRecords);
    }

    async editNextRecord(record, group) {
        const canProceed = await this.props.list.leaveEditMode({ validate: true });
        if (!canProceed) {
            return;
        }

        const iter = getRecordsUntilSection(this.props.list, record, true, true);
        if (this.isSection(record) || iter.sectionRecords.length === 1) {
            return this.props.list.addNewRecordAtIndex(iter.indexAtEnd - 1);
        } else {
            return super.editNextRecord(record, group);
        }
    }

    focusToName(editRec) {
        if (editRec && editRec.isNew && this.isSectionOrNote(editRec)) {
            const col = this.columns.find((c) => c.name === this.titleField);
            this.focusCell(col, null);
        }
    }

    hasNextSection(record) {
        return hasNextSection(this.props.list, record);
    }

    hasPreviousSection(record) {
        return hasPreviousSection(this.props.list, record);
    }

    isSectionOrNote(record = null) {
        record = record || this.record;
        return [DISPLAY_TYPES.SECTION, DISPLAY_TYPES.SUBSECTION, DISPLAY_TYPES.NOTE].includes(
            record.data.display_type
        );
    }

    isSection(record = null) {
        record = record || this.record;
        return [DISPLAY_TYPES.SECTION, DISPLAY_TYPES.SUBSECTION].includes(record.data.display_type);
    }

    isSortable() {
        return false;
    }

    isTopSection(record) {
        return record.data.display_type === DISPLAY_TYPES.SECTION;
    }

    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        return `${existingClasses} o_is_${record.data.display_type}`;
    }

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (
            this.isSectionOrNote(record) &&
            column.widget !== "handle" &&
            column.name !== this.titleField
        ) {
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
        const sectionCols = columns.filter(
            (col) =>
                col.widget === "handle" || (col.type === "field" && col.name === this.titleField)
        );
        return sectionCols.map((col) => {
            if (col.name === this.titleField) {
                return { ...col, colspan: columns.length - sectionCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }

    async moveSectionDown(record) {
        const canProceed = await this.props.list.leaveEditMode();
        if (!canProceed) {
            return;
        }

        const sectionRecords = getSectionRecords(this.props.list, record);
        const index = this.props.list.records.indexOf(record) + sectionRecords.length;
        const nextSectionRecords = getSectionRecords(this.props.list, this.props.list.records[index]);
        return this.swapSections(sectionRecords, nextSectionRecords);
    }

    async moveSectionUp(record) {
        const canProceed = await this.props.list.leaveEditMode();
        if (!canProceed) {
            return;
        }

        const previousSectionRecords = getPreviousSectionRecords(this.props.list, record);
        const sectionRecords = getSectionRecords(this.props.list, record);
        return this.swapSections(previousSectionRecords, sectionRecords);
    }

    async swapSections(sectionRecords1, sectionRecords2) {
        const commands = [];
        let sequence = sectionRecords1[0].data[this.props.list.handleField];
        for (const record of sectionRecords2) {
            commands.push(x2ManyCommands.update(record.resId || record._virtualId, {
                [this.props.list.handleField]: sequence++,
            }));
        }
        for (const record of sectionRecords1) {
            commands.push(x2ManyCommands.update(record.resId || record._virtualId, {
                [this.props.list.handleField]: sequence++,
            }));
        }
        await this.props.list.applyCommands(commands, { sort: true });
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
        return this.props.record.data.display_type === "line_section" ? CharField : TextField;
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
    additionalClasses: [...(x2ManyField.additionalClasses || []), "o_field_one2many"],
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
