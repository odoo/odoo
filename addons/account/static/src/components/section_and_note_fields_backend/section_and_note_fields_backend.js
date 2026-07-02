import { useExternalListener } from "@web/owl2/utils";
import { Component, computed, onWillUpdateProps, props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ListTextField, TextField } from "@web/views/fields/text/text_field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer, listRendererProps } from "@web/views/list/list_renderer";

const SHOW_ALL_ITEMS_TOOLTIP = _t("Some lines can be on the next page, display them to unlock actions on section.");
const DISABLED_MOVE_DOWN_ITEM_TOOLTIP = _t("Some lines of the next section can be on the next page, display them to unlock the action.");

const DISPLAY_TYPES = {
    NOTE: "line_note",
    SECTION: "line_section",
    SUBSECTION: "line_subsection",
};

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
    let index = list.records.findIndex(listRecord => listRecord.id === record.id);
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
    props = props({
        ...listRendererProps,
        aggregatedFields: t.any(),
        subsections: t.any(),
        hidePrices: t.any(),
        hideComposition: t.any(),
    });

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
        this.state.hoveredSectionId = null;
        this.state.focusedSectionId = null;
        this.patchedRecords = new WeakSet();
        this.sectionQtyClicked = false;
        this.sectionUOMClicked = false;
        this._mouseButtonDown = false;

        useExternalListener(document, "pointerdown", () => { this._mouseButtonDown = true; });
        useExternalListener(document, "pointerup", () => { this._mouseButtonDown = false; });

        if (Array.isArray(this.props?.list?.records)) {
            this.patchRecords(this.props.list.records);
        }

        onWillUpdateProps((nextProps) => {
            if (Array.isArray(nextProps?.list?.records)) {
                this.patchRecords(nextProps.list.records);
            }
        });
    }

    parentSectionMap = computed(() =>
        this.buildParentSectionMap(this.props.list.records)
    );

    /**
     * @override
     */
    async onCellClicked(record, column, ev) {
        if (column && column.name === "section_qty") {
            this.sectionQtyClicked = true;
        } else if (column && column.name === "section_uom_id") {
            this.sectionUOMClicked = true;
        } else {
            this.sectionQtyClicked = false;
            this.sectionUOMClicked = false;
        }
        return super.onCellClicked(record, column, ev);
    }

    /**
     * @override
     */
    focusCell(column, ...args) {
        const result = super.focusCell(column, ...args);
        if (this.sectionQtyClicked && this.isSection(this.editedRecord())) {
            this.sectionQtyClicked = false;
            const originalCol = this.columns.find(c => c.name === "product_uom_qty" || c.name === "quantity");
            if (originalCol) {
                return super.focusCell(originalCol, ...args);
            }
        }
        if (this.sectionUOMClicked && this.isSection(this.editedRecord())) {
            this.sectionUOMClicked = false;
            const originalCol = this.columns.find(c => c.name === "product_uom_id");
            if (originalCol) {
                return super.focusCell(originalCol, ...args);
            }
        }

        return result;
    }

    /**
     * @override
     * We don't want to display the `section_uom_id` field in the optional columns
     */
    get optionalFieldGroups() {
        const groups = super.optionalFieldGroups;
        return groups.map(group => {
            return {
                ...group,
                optionalFields: group.optionalFields.filter(field => field.name !== "section_uom_id")
            };
        });
    }

    patchRecords(records) {
        for (const record of records) {
            if (!this.patchedRecords.has(record)) {
                this.patchedRecords.add(record);
                const originalUpdate = record.update.bind(record);

                record.update = async (changes) => {
                    const isSectionQtyChanged = this.isSection(record) && "section_qty" in changes;
                    const isSectionUomChanged = this.isSection(record) && "section_uom_id" in changes;
                    let ratio = 1;

                    if (isSectionQtyChanged) {
                        const oldQty = record.data.section_qty || 1;
                        const newQty = changes.section_qty;
                        if (oldQty && newQty) {
                            ratio = oldQty !== 0 ? newQty / oldQty : newQty;
                        }
                    } else if (isSectionUomChanged) {
                        const oldUom = record.data.section_uom_id.id;
                        const newUom = changes.section_uom_id.id
                        if (oldUom && newUom && oldUom !== newUom) {
                            ratio = 1 / await this.env.services.orm.call(
                                "sale.order.line",
                                "compute_uom_ratio",
                                [],
                                {
                                    old_uom_id: oldUom,
                                    new_uom_id: newUom,
                                }
                            );
                        }
                    }

                    const result = await originalUpdate(changes);

                    if ((isSectionQtyChanged || isSectionUomChanged) && ratio !== 1) {
                        const updatePromises = [];
                        for (const child of getSectionRecords(this.props.list, record).filter(r => r.id !== record.id)) {
                            if (isSectionQtyChanged && this.isSection(child)) {
                                // Update subsection_qty visually without retriggering its onchange
                                updatePromises.push(child._update(
                                    { section_qty: child.data.section_qty * ratio },
                                    { withoutParentUpdate: true }
                                ));
                            } else if (!this.isSectionOrNote(child)) {
                                const qtyField = "product_uom_qty" in child.fields ? "product_uom_qty" : "quantity";
                                updatePromises.push(child._update(
                                    { [qtyField]: child.data[qtyField] * ratio },
                                    { withoutParentUpdate: true }
                                ));
                            }
                        }
                        await Promise.all(updatePromises);
                        await this.props.list._onUpdate();
                    }

                    return result;
                };
            }
        }
    }

    async onSectionMouseEnter(record) {
        if (!this.isSection(record) || this._mouseButtonDown) {
            return;
        }
        this.state.hoveredSectionId = record.id;
    }

    async onSectionMouseLeave(record) {
        if (!this.isSection(record) || this._mouseButtonDown) {
            return;
        }
        this.state.hoveredSectionId = null;
    }

    onSectionFocusIn(record) {
        if (!this.isSection(record)) return;
        this.state.focusedSectionId = record.id;
    }

    onSectionFocusOut(record, ev) {
        if (!this.isSection(record)) return;
        this.state.focusedSectionId = null;
    }

    get disabledMoveDownItemTooltip() {
        return DISABLED_MOVE_DOWN_ITEM_TOOLTIP;
    }

    get showAllItemsTooltip() {
        return SHOW_ALL_ITEMS_TOOLTIP;
    }

    hidePrices(record) {
        return record.data.collapse_prices;
    }

    hideComposition(record) {
        return record.data.collapse_composition;
    }

    disablePricesButton(record) {
        return (
            this.shouldCollapse(record, 'collapse_prices') || this.disableCompositionButton(record)
        );
    }

    disableCompositionButton(record) {
        return this.shouldCollapse(record, 'collapse_composition');
    }

    get sectionColumns() {
        return [...this.props.aggregatedFields, 'section_state', 'product_uom_qty', 'product_uom_id', 'quantity']
    }

    buildParentSectionMap(records) {
        const parentSectionMap = new Map();
        let lastSection = null;
        let lastSubSection = null;

        for (const record of records) {
            if (record.data.display_type === DISPLAY_TYPES.SECTION) {
                lastSection = record;
                lastSubSection = null;
                parentSectionMap.set(record, null);
            } else if (record.data.display_type === DISPLAY_TYPES.SUBSECTION) {
                lastSubSection = record;
                parentSectionMap.set(record, lastSection);
            } else {
                parentSectionMap.set(record, lastSubSection ?? lastSection);
            }
        }
        return parentSectionMap;
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
        const context = this.getInsertLineContext(record, addSubSection);
        if (addSubSection) {
            context["default_display_type"] = DISPLAY_TYPES.SUBSECTION;
        }
        await this.props.list.addNewRecordAtIndex(index, { context });
    }

    /**
     * Hook for other modules to conditionally specify defaults for new lines
     */
    getInsertLineContext(_record, _addSubSection) {
        return {};
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
        if (this.editedRecord() && this.editedRecord() !== record) {
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
        if (iter.sectionRecords.length === 1) {
            return this.props.list.addNewRecordAtIndex(iter.sectionIndex - 1);
        } else {
            return super.editNextRecord(record, group);
        }
    }

    expandPager() {
        return this.props.list.load({ limit: this.props.list.count });
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
        return [DISPLAY_TYPES.SECTION, DISPLAY_TYPES.SUBSECTION, DISPLAY_TYPES.NOTE].includes(
            record.data.display_type
        );
    }

    isSection(record = null) {
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
     * @param {boolean} checkSection - if true, also evaluates the collapse state for section or
     *  subsection records
     * @returns {boolean}
     */
    shouldCollapse(record, fieldName, checkSection = false) {
        const parentSection = this.parentSectionMap().get(record);

        // --- For sections ---
        if (this.isSection(record) && checkSection) {
            if (this.isTopSection(record)) {
                return record.data[fieldName];
            }
            if (this.isSubSection(record)) {
                return record.data[fieldName] || parentSection?.data[fieldName];
            }
            return false;
        }

        // `line_section` never collapses unless explicitly checked above
        if (this.isTopSection(record)) {
            return false;
        }

        if (!parentSection) {
            return false;
        }

        // --- For regular lines ---
        if (this.isSubSection(parentSection)) {
            const grandParent = this.parentSectionMap().get(parentSection);
            return parentSection.data[fieldName] || grandParent?.data[fieldName];
        }

        return !!parentSection.data[fieldName];
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
        if (this.isSection(record) && record.isInEdition) {
            classNames += " border-bottom-0";
        }
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
        // Remove bold and add muted effect on section_qty and section_uom_id
        if (this.isSection(record) && ["section_qty", "section_uom_id"].includes(column.name)) {
            classNames += " fw-normal text-muted";
        }

        return classNames;
    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isSectionOrNote(record)) {
            return this.getSectionAndNoteColumns(columns, record);
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

    changeFieldSection(columns, record) {
        columns = columns.map(col => {
            if (col.name === "product_uom_qty") {
                return {
                    ...col,
                    name: "section_qty",
                };
            }
            if (col.name === "quantity") {
                return {
                    ...col,
                    name: "section_qty",
                };
            }
            if (col.name === "product_uom_id") {
                return {
                    ...col,
                    name: "section_uom_id",
                };
            }
            return { ...col };
        });
        return columns;
    }

    getSectionAndNoteColumns(columns, record) {
        let sectionCols = columns.filter(
            (col) =>
                col.widget === "handle"
                || col.name === this.titleField
                || (this.isSection(record) && this.sectionColumns.includes(col.name))
        );
        columns = this.changeFieldSection(columns, record);
        sectionCols = this.changeFieldSection(sectionCols, record);
        const showQtyUnit = this.state.hoveredSectionId === record.id || this.state.focusedSectionId === record.id;
        if (showQtyUnit) {
            const isSectionCol = (col) => sectionCols.some((s) => s.id === col.id);
            const titleIndex = columns.findIndex((col) => col.name === this.titleField);
            const colspanBonus = columns.slice(0, titleIndex).filter((col) => !isSectionCol(col)).length;
            return columns.flatMap((col, i) => {
                if (col.name === this.titleField) return [colspanBonus ? { ...col, colspan: colspanBonus + 1 } : col];
                if (i < titleIndex && !isSectionCol(col)) return []; // absorbed by colspan
                return [isSectionCol(col) ? col : { ...col, invisible: "1" }];
            });
        }
        sectionCols = sectionCols.filter(
            (col) => !["section_qty", "section_uom_id"].includes(col.name)
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

    /**
     * @override
     * Reset the values of `collapse_` fields of the subsection if it is dragged
     */
    async sortDrop(dataRowId, dataGroupId, options) {
        await super.sortDrop(dataRowId, dataGroupId, options);

        const record = this.props.list.records.find(r => r.id === dataRowId);
        const parentSection = this.parentSectionMap().get(record);
        const commands = [];

        if (this.resetOnResequence(record, parentSection)) {
            commands.push(x2ManyCommands.update(record.resId || record._virtualId, {
                ...this.fieldsToReset(),
            }));
        }

        await this.props.list.applyCommands(commands);
    }

    resetOnResequence(record, parentSection) {
        return (
            this.isSubSection(record)
            && parentSection?.data.collapse_composition
            && (record.data.collapse_composition || record.data.collapse_prices)
        );
    }

    fieldsToReset() {
        return {
            ...(this.props.hideComposition && { collapse_composition: false }),
            ...(this.props.hidePrices && { collapse_prices: false }),
        };
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
        return TextField;
    }
}

export class ListSectionAndNoteText extends SectionAndNoteText {
    get componentToUse() {
        return ListTextField;
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
