/** @odoo-module native */
import {
    ProductLabelSectionAndNoteListRender,
    ProductLabelSectionAndNoteOne2Many,
    productLabelSectionAndNoteOne2Many,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field_o2m";
import {
    getSectionRecords,
    ListSectionAndNoteText,
    listSectionAndNoteText,
    sectionAndNoteFieldOne2Many,
    SectionAndNoteText,
    sectionAndNoteText,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { useSubEnv } from "@odoo/owl";
import {
    getRecordsToRecompute,
    handleQuantityAdjustment,
} from "@sale/js/section_optional_line_utils";
import { makeContext } from "@web/core/context";
import { x2ManyCommands } from "@web/core/network";
import { registry } from "@web/core/registry";
import { CharField } from "@web/fields/basic/char/char_field";
import { listId } from "@web/model/relational_model";

const indexOfRecord = (records, record) => records.findIndex((r) => r.id === record.id);

export function getComboRecords(listRecords, record) {
    const comboRecords = [];

    if (record.data.product_type === "combo") {
        comboRecords.push(record);
        let index = indexOfRecord(listRecords, record) + 1;

        while (index < listRecords.length) {
            const r = listRecords[index];
            if (
                !r.data.combo_item_id?.id ||
                (r.data.linked_line_id?.id !== record.resId &&
                    r.data.linked_virtual_id !== record.data.virtual_id)
            ) {
                break;
            }
            comboRecords.push(r);
            index++;
        }
    } else if (record.data.combo_item_id?.id) {
        let index = indexOfRecord(listRecords, record);
        while (index >= 0) {
            const r = listRecords[index];
            comboRecords.unshift(r);

            if (
                r.data.product_type === "combo" &&
                (r.resId === record.data.linked_line_id?.id ||
                    r.data.virtual_id === record.data.linked_virtual_id)
            ) {
                break;
            }
            index--;
        }
    }

    return comboRecords;
}

export class SaleOrderLineListRenderer extends ProductLabelSectionAndNoteListRender {
    static recordRowTemplate = "sale.ListRenderer.RecordRow";

    setup() {
        super.setup();
        this.priceColumns.push("discount");
        this.copyFields.push("is_optional");

        useSubEnv({
            shouldCollapse: this.shouldCollapse.bind(this),
        });
    }

    /** @override */
    buildRowApi() {
        const rec = (record) => this.resolveRowRecord(record);
        return {
            ...super.buildRowApi(),
            isCombo: (record) => this.isCombo(rec(record)),
            getComboColumns: () => this.comboColumns,
            getPreviousRecords: (record) => this.getPreviousRecords(rec(record)),
            getNextRecords: (record) => this.getNextRecords(rec(record)),
            moveCombo: (record, direction) => this.moveCombo(rec(record), direction),
            onDeleteRecord: (record) => this.onDeleteRecord(rec(record)),
            disableOptionalButton: (record) => this.disableOptionalButton(record),
            toggleIsOptional: (record) => this.toggleIsOptional(rec(record)),
        };
    }

    get comboColumns() {
        return [
            this.titleField,
            ...this.props.aggregatedFields,
            "product_qty",
            "discount",
        ];
    }

    getCellTitle(column, record) {
        if (column.name === "product_id" || column.name === "product_template_id") {
            return;
        }
        return super.getCellTitle(column, record);
    }

    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        const productTmplCol = activeColumns.find(
            (col) => col.name === "product_template_id",
        );
        const productCol = activeColumns.find((col) => col.name === "product_id");

        if (productCol && productTmplCol) {
            activeColumns = activeColumns.filter(
                (col) => col.name !== "product_template_id",
            );
        }

        return activeColumns;
    }

    getRowClass(record) {
        let classNames = super.getRowClass(record);
        if (this.isCombo(record) || this.isComboItem(record)) {
            classNames = classNames.replace("o_row_draggable", "");
        }
        classNames = `${classNames} ${this.isCombo(record) ? "o_is_line_section o_is_line_section_no_indent" : ""}`;
        if (this.shouldCollapse(record, "is_optional", true)) {
            classNames += " text-primary";
        }
        return classNames;
    }

    isCellReadonly(column, record) {
        return (
            super.isCellReadonly(column, record) ||
            (this.isComboItem(record) &&
                !["name", "tax_ids", "qty_transferred"].includes(column.name))
        );
    }

    async onDeleteRecord(record) {
        if (this.isCombo(record)) {
            await record.update({ selected_combo_items: JSON.stringify([]) });
        }
        await super.onDeleteRecord(record);
    }

    async moveCombo(record, direction) {
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
        if (!canProceed) {
            return;
        }

        const wasOptional = this.shouldCollapse(record, "is_optional");
        const { movingRecords, targetRecords } = this.getComboSwapPairs(
            record,
            direction,
        );
        await this.swapSections(movingRecords, targetRecords);

        const isOptional = this.shouldCollapse(record, "is_optional");
        const qtyField = this.optionalQuantityField;
        if (wasOptional && !isOptional && !record.data[qtyField]) {
            await record.update({ [qtyField]: 1 });
        } else if (!wasOptional && isOptional) {
            await record.update({ [qtyField]: 0 });
        }
    }

    getComboSwapPairs(record, direction) {
        const comboRecords = getComboRecords(this.props.list.records, record);

        if (direction === "up") {
            return {
                movingRecords: this.getPreviousRecords(record),
                targetRecords: comboRecords,
            };
        }
        if (direction === "down") {
            return {
                movingRecords: comboRecords,
                targetRecords: this.getNextRecords(record),
            };
        }
        return { movingRecords: [], targetRecords: [] };
    }

    getPreviousRecords(record) {
        const { records } = this.props.list;
        const previousRecord = records[indexOfRecord(records, record) - 1];

        if (previousRecord?.data.combo_item_id?.id) {
            return getComboRecords(records, previousRecord);
        }
        return previousRecord ? [previousRecord] : false;
    }

    getNextRecords(record) {
        const { records } = this.props.list;
        const comboRecords = getComboRecords(records, record);

        const nextRecord =
            records[indexOfRecord(records, record) + comboRecords.length];
        if (nextRecord?.data.product_type === "combo") {
            return getComboRecords(records, nextRecord);
        }
        return nextRecord ? [nextRecord] : false;
    }

    canUseFormatter(column, record) {
        if (this.isCombo(record) && this.props.aggregatedFields.includes(column.name)) {
            return true;
        }
        return super.canUseFormatter(column, record);
    }

    getFormattedValue(column, record) {
        if (this.isCombo(record) && this.props.aggregatedFields.includes(column.name)) {
            const total = getComboRecords(this.props.list.records, record).reduce(
                (total, record) => total + record.data[column.name],
                0,
            );

            const formatter = registry
                .category("formatters")
                .get(column.fieldType, (val) => val);

            return formatter(total, {
                ...formatter.extractOptions?.(column),
                data: record.data,
                field: record.fields[column.name],
            });
        }
        return super.getFormattedValue(column, record);
    }

    isCombo(record) {
        return record.data.product_type === "combo";
    }

    isComboItem(record) {
        return !!record.data.combo_item_id;
    }

    shouldDuplicateSectionItem(record) {
        return !this.isCombo(record) && !this.isComboItem(record);
    }

    displayDeleteIcon(record) {
        return super.displayDeleteIcon(record) && !this.isComboItem(record);
    }

    /** @see handleQuantityAdjustment in section_optional_line_utils.js — */
    get optionalQuantityField() {
        return "product_qty";
    }

    disableCompositionButton(record) {
        return (
            super.disableCompositionButton(record) ||
            this.shouldCollapse(record, "is_optional", true)
        );
    }

    disablePricesButton(record) {
        return (
            super.disablePricesButton(record) ||
            this.shouldCollapse(record, "is_optional", true)
        );
    }

    disableOptionalButton(record) {
        return (
            this.shouldCollapse(record, "is_optional") ||
            this.shouldCollapse(record, "collapse_prices", true) ||
            this.shouldCollapse(record, "collapse_composition", true)
        );
    }

    /** @override */
    getRowProps(record, group, groupId) {
        return {
            ...super.getRowProps(record, group, groupId),
            mutedOptional: this.shouldCollapse(record, "is_optional", true),
        };
    }

    get isCurrentSectionOptional() {
        if (this.props.list.records.length === 0) {
            return false;
        }

        return this.shouldCollapse(
            this.props.list.records[this.props.list.records.length - 1],
            "is_optional",
            true,
        );
    }

    add(params) {
        params.context = this.getCreateContext(params);
        super.add(params);
    }

    getCreateContext(params) {
        const evaluatedContext = makeContext([params.context]);
        if (
            !evaluatedContext[`default_display_type`] &&
            this.isCurrentSectionOptional
        ) {
            return {
                ...evaluatedContext,
                [`default_${this.optionalQuantityField}`]: 0,
            };
        }
        return params.context;
    }

    getInsertLineContext(record, addSubSection) {
        if (this.shouldCollapse(record, "is_optional", true) && !addSubSection) {
            return {
                ...super.getInsertLineContext(record, addSubSection),
                [`default_${this.optionalQuantityField}`]: 0,
            };
        }
        return super.getInsertLineContext(record, addSubSection);
    }

    /** @override */
    async toggleCollapse(record, fieldName) {
        await super.toggleCollapse(record, fieldName);

        if (this.isTopSection(record) && record.data[fieldName]) {
            const commands = [];

            for (const sectionRecord of getSectionRecords(this.props.list, record)) {
                if (this.isSubSection(sectionRecord)) {
                    commands.push(
                        x2ManyCommands.update(listId(sectionRecord), {
                            is_optional: false,
                        }),
                    );
                }
            }

            if (commands.length) {
                await this.props.list.applyCommands(commands, { sort: true });
            }
        }
    }

    async toggleIsOptional(record) {
        const setOptional = !record.data.is_optional;
        const qtyField = this.optionalQuantityField;

        const commands = [
            x2ManyCommands.update(listId(record), {
                is_optional: setOptional,
            }),
        ];

        const linesToRestock = [];
        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                if (setOptional) {
                    changes = { [qtyField]: 0, price_total: 0, price_subtotal: 0 };
                } else {
                    linesToRestock.push(sectionRecord);
                }
            } else if (this.isSubSection(sectionRecord)) {
                changes = setOptional && {
                    collapse_composition: false,
                    collapse_prices: false,
                };
            }

            if (Object.keys(changes).length) {
                commands.push(x2ManyCommands.update(listId(sectionRecord), changes));
            }
        }

        await this.props.list.applyCommands(commands, { sort: true });
        await Promise.all(
            linesToRestock.map((line) =>
                line.update({ [qtyField]: line.data[qtyField] || 1 }),
            ),
        );
    }

    /** @override */
    async sortDrop(dataRowId, dataGroupId, { element, previous }) {
        const record = this.props.list.records.find((r) => r.id === dataRowId);
        const recordMap = this._getRecordsToRecompute(
            record,
            previous ? previous.dataset.id : null,
        );

        await super.sortDrop(dataRowId, dataGroupId, { element, previous });

        await this._handleQuantityAdjustment(recordMap);
    }

    /** @see getRecordsToRecompute in section_optional_line_utils.js — shared */
    _getRecordsToRecompute(record, targetId) {
        return getRecordsToRecompute(this, record, targetId);
    }

    /** @see handleQuantityAdjustment in section_optional_line_utils.js — */
    async _handleQuantityAdjustment(recordMap) {
        return handleQuantityAdjustment(this, recordMap);
    }

    /** @override */
    resetOnResequence(record, parentSection) {
        return (
            super.resetOnResequence(record, parentSection) ||
            (this.isSubSection(record) &&
                parentSection?.data.is_optional &&
                (record.data.collapse_composition ||
                    record.data.collapse_prices ||
                    record.data.is_optional))
        );
    }

    fieldsToReset() {
        return { ...super.fieldsToReset(), is_optional: false };
    }
}

export class SaleOrderLineOne2Many extends ProductLabelSectionAndNoteOne2Many {
    static components = {
        ...ProductLabelSectionAndNoteOne2Many.components,
        ListRenderer: SaleOrderLineListRenderer,
    };
}
export const saleOrderLineOne2Many = {
    ...productLabelSectionAndNoteOne2Many,
    component: SaleOrderLineOne2Many,
    additionalClasses: sectionAndNoteFieldOne2Many.additionalClasses,
};

registry.category("fields").add("sol_o2m", saleOrderLineOne2Many);

export class SaleOrderLineText extends SectionAndNoteText {
    get componentToUse() {
        return this.props.record.data.product_type === "combo"
            ? CharField
            : super.componentToUse;
    }
}

export class ListSaleOrderLineText extends ListSectionAndNoteText {
    get componentToUse() {
        return this.props.record.data.product_type === "combo"
            ? CharField
            : super.componentToUse;
    }
}

export const saleOrderLineText = {
    ...sectionAndNoteText,
    component: SaleOrderLineText,
};

export const listSaleOrderLineText = {
    ...listSectionAndNoteText,
    component: ListSaleOrderLineText,
};

registry.category("fields").add("sol_text", saleOrderLineText);
registry.category("fields").add("list.sol_text", listSaleOrderLineText);
