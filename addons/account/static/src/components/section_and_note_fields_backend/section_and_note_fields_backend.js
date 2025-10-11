import { Component, useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ListTextField, TextField } from "@web/views/fields/text/text_field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";

const SHOW_ALL_ITEMS_TOOLTIP = _t("Some lines can be on the next page, display them to unlock actions on section.");
const DISABLED_MOVE_DOWN_ITEM_TOOLTIP = _t("Some lines of the next section can be on the next page, display them to unlock the action.");

const DISPLAY_TYPES = {
    NOTE: "line_note",
    SECTION: "line_section",
    SUBSECTION: "line_subsection",
};

export function getParentSectionRecord(list, record) {
    const { sectionIndex } = getRecordsUntilSection(list, record, false, record.data.display_type !== DISPLAY_TYPES.SUBSECTION);
    return list.records[sectionIndex];
}

function getPreviousSectionRecords(list, record) {
    const { sectionRecords } = getRecordsUntilSection(list, record, false);
    return sectionRecords;
}

export function getSectionRecords(list, record, subSection) {
    const { sectionRecords } = getRecordsUntilSection(list, record, true, subSection);
    return sectionRecords;
}

function hasNextSection(list, record) {
    const { sectionIndex } = getRecordsUntilSection(list, record, true);
    return sectionIndex < list.records.length && list.records[sectionIndex].data.display_type === record.data.display_type;
}

function hasPreviousSection(list, record) {
    const { sectionIndex } = getRecordsUntilSection(list, record, false);
    return sectionIndex >= 0 && list.records[sectionIndex].data.display_type === record.data.display_type;
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
        sectionIndex: index,
    };
}

export class SectionAndNoteListRenderer extends ListRenderer {
    static template = "account.SectionAndNoteListRenderer";
    static recordRowTemplate = "account.SectionAndNoteListRenderer.RecordRow";
    static props = [
        ...super.props,
        "aggregatedFields",
        "subsections",
        "hidePrices",
        "hideComposition",
    ];

    /**
     * The purpose of this extension is to allow sections and notes in the one2many list
     * primarily used on Sales Orders and Invoices
     *
     * @override
     */
    setup() {
        super.setup();
        this.titleField = "name";
        this.priceColumns = [...this.props.aggregatedFields, "price_unit"];
        // invisible fields to force copy when duplicating a section
        this.copyFields = ["display_type", "collapse_composition", "collapse_prices"];
        useEffect(
            (editedRecord) => this.focusToName(editedRecord),
            () => [this.editedRecord]
        );
    }

    get disabledMoveDownItemTooltip() {
        return DISABLED_MOVE_DOWN_ITEM_TOOLTIP;
    }

    get showAllItemsTooltip() {
        return SHOW_ALL_ITEMS_TOOLTIP;
    }

    get hidePrices() {
        return this.record.data.collapse_prices;
    }

    get hideCompositions() {
        return this.record.data.collapse_composition;
    }

    get showPricesButton() {
        if (this.isSubSection(this.record)) {
            const parentRecord = getParentSectionRecord(this.props.list, this.record);
            return !parentRecord?.data?.collapse_prices && !parentRecord?.data?.collapse_composition;
        }
        return true;
    }

    get showCompositionButton() {
        if (this.isSubSection(this.record)) {
            const parentRecord = getParentSectionRecord(this.props.list, this.record);
            return !parentRecord?.data?.collapse_composition;
        }
        return true;
    }

    async toggleCollapse(record, fieldName) {
        // We don't want to have 'collapse_prices' & 'collapse_composition' set to True at the same time
        const reverseFieldName = fieldName === 'collapse_prices' ? 'collapse_composition' : 'collapse_prices';
        const changes = {
            [fieldName]: !record.data[fieldName],
            [reverseFieldName]: false,
        };
        await record.update(changes);
    }

    async addRowAfterSection(record, addSubSection) {
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
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
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
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
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
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

    canUseFormatter(column, record) {
        if (
            this.isSection(record) &&
            this.props.aggregatedFields.includes(column.name)
        ) {
            return true;
        }
        return super.canUseFormatter(column, record);
    }

    async deleteSection(record) {
        if (this.editedRecord && this.editedRecord !== record) {
            const left = await this.props.list.leaveEditMode({ canAbandon: false });
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

        const { sectionRecords, sectionIndex } = getRecordsUntilSection(this.props.list, record, true)
        const recordsToDuplicate = sectionRecords.filter((record) => {
            return this.shouldDuplicateSectionItem(record);
        });
        await this.props.list.duplicateRecords(recordsToDuplicate, {
            targetIndex: sectionIndex,
            copyFields: this.copyFields,
        });
    }

    async editNextRecord(record, group) {
        const canProceed = await this.props.list.leaveEditMode({ validate: true });
        if (!canProceed) {
            return;
        }

        const iter = getRecordsUntilSection(this.props.list, record, true, true);
        if (this.isSection(record) || iter.sectionRecords.length === 1) {
            return this.props.list.addNewRecordAtIndex(iter.sectionIndex - 1);
        } else {
            return super.editNextRecord(record, group);
        }
    }

    expandPager() {
        return this.props.list.load({ limit: this.props.list.count });
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

    isNextSectionInPage(record) {
        if (this.props.list.count <= this.props.list.offset + this.props.list.limit) {
            // if last page
            return true;
        }
        const sectionRecords = getSectionRecords(this.props.list, record);
        const index = this.props.list.records.indexOf(record) + sectionRecords.length;
        if (index >= this.props.list.limit) {
            return false;
        }

        const { sectionIndex } = getRecordsUntilSection(this.props.list, this.props.list.records[index], true);
        return sectionIndex < this.props.list.limit;
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

    isSectionInPage(record) {
        if (this.props.list.count <= this.props.list.offset + this.props.list.limit) {
            // if last page
            return true;
        }
        const { sectionIndex } = getRecordsUntilSection(this.props.list, record, true);
        return sectionIndex < this.props.list.limit;
    }

    isSortable() {
        return false;
    }

    isTopSection(record) {
        return record.data.display_type === DISPLAY_TYPES.SECTION;
    }

    isSubSection(record) {
        return record.data.display_type === DISPLAY_TYPES.SUBSECTION;
    }

    /**
     * Determines whether the line should be collapsed.
     * - If the parent is a section: use the parent’s field.
     * - If the parent is a subsection: use parent subsection OR its section.
     * @param {object} record
     * @param {string} fieldName
     * @returns {boolean}
     */
    shouldCollapse(record, fieldName) {
        if (this.isTopSection(record)) {
            return false;
        } else {
            const parentSection = getParentSectionRecord(this.props.list, record);
            if (parentSection?.data.display_type === DISPLAY_TYPES.SUBSECTION) {
                return (
                    parentSection.data[fieldName]
                    || getParentSectionRecord(this.props.list, parentSection)?.data[fieldName]
                );
            }
            return parentSection?.data[fieldName];
        }
    }

    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        let newClasses = `${existingClasses} o_is_${record.data.display_type}`;
        if (this.props.hideComposition && this.shouldCollapse(record, 'collapse_composition')) {
            newClasses += " text-muted";
        }
        return newClasses;
    }

    getCellClass(column, record) {
        let classNames = super.getCellClass(column, record);
        // For hiding columnns of section and note
        if (
            this.isSectionOrNote(record)
            && column.widget !== "handle"
            && ![column.name, ...this.props.aggregatedFields].includes(column.name)
        ) {
            return `${classNames} o_hidden`;
        }
        // For muting the price columns
        if (
            this.props.hidePrices
            && this.shouldCollapse(record, 'collapse_prices')
            && this.priceColumns.includes(column.name)
        ) {
            classNames += " text-muted";
        }

        return classNames;
    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isSectionOrNote(record)) {
            return this.getSectionColumns(columns, record);
        }
        return columns;
    }

    getFormattedValue(column, record) {
        if (this.isSection(record) && this.props.aggregatedFields.includes(column.name)) {
            const total = getSectionRecords(this.props.list, record)
                .filter((record) => !this.isSection(record))
                .reduce((total, record) => total + record.data[column.name], 0);
            const formatter = registry.category("formatters").get(column.fieldType, (val) => val);
            return formatter(total, {
                ...formatter.extractOptions?.(column),
                data: record.data,
                field: record.fields[column.name],
            });
        }
        return super.getFormattedValue(column, record);
    }

    getSectionColumns(columns, record) {
        const sectionCols = columns.filter(
            (col) =>
                col.widget === "handle"
                || col.name === this.titleField
                || (this.isSection(record) && this.props.aggregatedFields.includes(col.name))
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
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
        if (!canProceed) {
            return;
        }

        const sectionRecords = getSectionRecords(this.props.list, record);
        const index = this.props.list.records.indexOf(record) + sectionRecords.length;
        const nextSectionRecords = getSectionRecords(this.props.list, this.props.list.records[index]);
        return this.swapSections(sectionRecords, nextSectionRecords);
    }

    async moveSectionUp(record) {
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
        if (!canProceed) {
            return;
        }

        const previousSectionRecords = getPreviousSectionRecords(this.props.list, record);
        const sectionRecords = getSectionRecords(this.props.list, record);
        return this.swapSections(previousSectionRecords, sectionRecords);
    }

    shouldDuplicateSectionItem(record) {
        return true;
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
        ...super.components,
        ListRenderer: SectionAndNoteListRenderer,
    };
    static props = {
        ...super.props,
        aggregatedFields: Array,
        hideComposition: Boolean,
        hidePrices: Boolean,
        subsections: Boolean,
    };

    get rendererProps() {
        const rp = super.rendererProps;
        if (this.props.viewMode === "list") {
            rp.aggregatedFields = this.props.aggregatedFields;
            rp.hideComposition = this.props.hideComposition;
            rp.hidePrices = this.props.hidePrices;
            rp.subsections = this.props.subsections;
        }
        return rp;
    }
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
    extractProps: (staticInfo, dynamicInfo) => {
        return {
            ...x2ManyField.extractProps(staticInfo, dynamicInfo),
            aggregatedFields: staticInfo.attrs.aggregated_fields
                ? staticInfo.attrs.aggregated_fields.split(/\s*,\s*/)
                : [],
            hideComposition: staticInfo.options?.hide_composition ?? false,
            hidePrices: staticInfo.options?.hide_prices ?? false,
            subsections: staticInfo.options?.subsections ?? false,
        };
    },
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
