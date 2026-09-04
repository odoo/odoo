import { useSubEnv } from "@web/owl2/utils";
import {
    ProductLabelSectionAndNoteListRender,
    productLabelSectionAndNoteOne2Many,
    ProductLabelSectionAndNoteOne2Many,
} from "@account/components/product_label_section_and_note_o2m/product_label_section_and_note_field_o2m";
import {
    getSectionRecords,
    sectionAndNoteFieldOne2Many,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { getFieldsSpec } from "@web/model/relational_model/utils";

function getComboRecords(listRecords, record) {
    const comboRecords = [];

    if (record.data.product_type === 'combo') {
        // if currernt record is combo then we move forward util we find non combo line
        comboRecords.push(record);
        let index = listRecords.indexOf(record) + 1;

        while (index < listRecords.length) {
            const r = listRecords[index];
            if (
                !r.data.combo_item_id?.id
                || (
                    r.data.linked_line_id?.id !== record.resId
                    && r.data.linked_virtual_id !== record.data.virtual_id
                )
            ) {
                break;
            }
            comboRecords.push(r);
            index++;
        }

    } else if (record.data.combo_item_id?.id) {
        // if current record is combo item then we move backward util we find associated combo line
        // Here we assume that the record we get is the last item of the combo
        let index = listRecords.indexOf(record);
        while (index >= 0) {
            const r = listRecords[index];
            comboRecords.unshift(r);

            if (
                r.data.product_type === 'combo'
                && (
                    r.resId === record.data.linked_line_id?.id
                    || r.data.virtual_id === record.data.linked_virtual_id
                )
            ) {
                break;
            }
            index--;
        }
    }

    return comboRecords;
}

export class SaleOrderLineListRenderer extends ProductLabelSectionAndNoteListRender {
    static recordRowTemplate = 'sale.ListRenderer.RecordRow';

    setup() {
        super.setup();
        this.priceColumns.push('discount');
        this.adjustingSectionQuantities = false;

        useSubEnv({
            shouldCollapse: this.shouldCollapse.bind(this),
            adjustSectionQuantities: this.adjustSectionQuantities.bind(this),
        });
    }

    /**
     * Little hack to make sure we get correct title field everytime
     * while accessing comboColumns
     */
    get comboColumns() {
        return [this.titleField, ...this.props.aggregatedFields, 'product_uom_qty', 'discount'];
    }

    get sectionColumns() {
        return [...super.sectionColumns, "line_number", "sol_qty", "sol_uom"];
    }

    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        // Hide the UOM column if the field is optional and not active
        const uomCol = activeColumns.find((col) => col.name === "sol_uom");
        if (uomCol) {
            const uomField = uomCol.fields.find((field) => field.name === "product_uom_id");
            if (!uomField || (uomField.optional && !this.optionalActiveFields[uomField.name])) {
                activeColumns = activeColumns.filter((col) => col.name !== "sol_uom");
            }
        }

        return activeColumns;
    }

    isColumnGroupFieldVisible(fieldInfo, record) {
        const isColumnVisible = super.isColumnGroupFieldVisible(fieldInfo, record);
        if (!isColumnVisible) {
            return false;
        }

        // Hide the template field if variant one is active
        if (fieldInfo.name === "product_template_id") {
            return !this.optionalActiveFields["product_id"];
        }

        return true;
    }

    isProductFieldActive() {
        return (
            this.optionalActiveFields["product_id"]
            || this.optionalActiveFields["product_template_id"]
        );
    }

    getRowClass(record) {
        let classNames = super.getRowClass(record);
        if (this.isCombo(record) || this.isComboItem(record)) {
            classNames = classNames.replace('o_row_draggable', '');
        }
        return `${classNames} ${this.isCombo(record) ? 'fw-bold' : ''}`;
    }

    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record).split(" ");
        if (column.name == "name" && record.isFieldInvalid("product_template_id")) {
            classNames.push("o_invalid_cell o_required_modifier");
        }
        return classNames.join(" ");
    }

    /**
     * @override
     */
    focusToName(editRec) {
        if (editRec && editRec.isNew && this.isSection(editRec)) {
            // Don't always focus on `titleField` for sections since we are adding section_qty and
            // section_uom_id fields in section row.
            return;
        }
        super.focusToName(editRec);
    }

    async adjustSectionQuantities(record, ratio) {
        if (ratio === 1 || this.adjustingSectionQuantities) {
            return;
        }

        const sectionLines = getSectionRecords(
            this.props.list,
            record,
            this.isSubSection(record)
        ).filter((line) => !this.isNote(line) && !this.isComboItem(line) && line !== record);

        if (!sectionLines.length) {
            return;
        }

        const linesById = {};
        const sectionLinesData = {};
        const commands = [];
        const orderChanges = {
            order_id: {
                ...(await this.props.list._parent.getChanges()),
                ...(!this.props.list._parent.isNew && { id: this.props.list._parent.resId }),
            },
        };

        for (const sectionLine of sectionLines) {
            const qtyField = this.isSection(sectionLine) ? "section_qty" : "product_uom_qty";
            const lineId = sectionLine.resId || sectionLine._virtualId;
            linesById[lineId] = sectionLine;
            sectionLinesData[lineId] = {
                ids: sectionLine.resId ? [sectionLine.resId] : [],
                changes: {
                    ...(await sectionLine.getChanges({ withReadonly: true })),
                    [qtyField]: sectionLine.data[qtyField] * ratio,
                },
                changed_fields: [qtyField],
            };
            commands.push(
                x2ManyCommands.update(lineId, {
                    [qtyField]: sectionLine.data[qtyField] * ratio,
                })
            );
        }

        const fieldsSpec = getFieldsSpec(
            this.props.list.activeFields,
            this.props.list.fields,
            this.props.list.evalContext,
            { withInvisible: true }
        );
        const results = await this.orm.call("sale.order", "batch_onchange_sol", [
            sectionLinesData,
            orderChanges,
            fieldsSpec,
        ]);

        commands.push(
            ...Object.entries(results).map(([lineId, values]) => {
                const id = linesById[lineId].resId || linesById[lineId]._virtualId;
                return x2ManyCommands.update(id, values);
            })
        );

        // To make sure rpc isn't called recursively for subsections when updating the quantities of
        // parent section lines.
        this.adjustingSectionQuantities = true;
        await this.props.list.applyCommands(commands);
        this.adjustingSectionQuantities = false;
    }

    /**
     * @override
     */
    getSectionAndNoteColumns(columns, record) {
        if (this.isNote(record)) {
            return super.getSectionAndNoteColumns(columns, record);
        }
        return this.getSectionColumns(columns);
    }

    getSectionColumns(columns) {
        const isSectionCol = (col) =>
            [this.titleField, ...this.sectionColumns].includes(col.name) || col.widget === "handle";

        let titleColspan = 1;
        let absorbingColumns = true;
        let titleCol;

        const sectionCols = [];

        for (const col of columns) {
            if (col.name === this.titleField) {
                titleCol = col;
                continue;
            }

            if (isSectionCol(col)) {
                if (titleCol) {
                    // Stop absorbing at the first section column after the title.
                    absorbingColumns = false;
                    sectionCols.push({ ...titleCol, colspan: titleColspan }, col);
                    // Empty titleCol so that we don't add it again if there are multiple section
                    // columns after this.
                    titleCol = null;
                } else {
                    sectionCols.push(col);
                }
                continue;
            }

            if (absorbingColumns) {
                // Absorb non-section columns into the title's colspan.
                titleColspan++;
                continue;
            }

            sectionCols.push({ ...col, invisible: "1", readonly: "1" });
        }

        return sectionCols;
    }

    isCellReadonly(column, record) {
        return super.isCellReadonly(column, record) || (
            this.isComboItem(record)
                && !['name', 'tax_ids', 'qty_delivered'].includes(column.name)
        );
    }

    async onDeleteRecord(record) {
        if (this.isCombo(record)) {
            await record.update({ selected_combo_items: "[]" });
        }
        await super.onDeleteRecord(record);
    }

    async moveCombo(record, direction) {
        const canProceed = await this.props.list.leaveEditMode({ canAbandon: false });
        if (!canProceed) return;

        const { movingRecords, targetRecords } = this.getComboSwapPairs(record, direction);
        return this.swapSections(movingRecords, targetRecords);
    }

    getComboSwapPairs(record, direction) {
        const comboRecords = getComboRecords(this.props.list.records, record);

        if (direction === 'up') {
            return {
                movingRecords: this.getPreviousRecords(record),
                targetRecords: comboRecords,
            };
        }
        if (direction === 'down') {
            return {
                movingRecords: comboRecords,
                targetRecords: this.getNextRecords(record),
            };
        }
        return { movingRecords: [], targetRecords: [] };
    }

    getPreviousRecords(record) {
        const { records } = this.props.list;
        const previousRecord = records[records.indexOf(record) - 1];

        if (previousRecord?.data.combo_item_id?.id){
            return getComboRecords(records, previousRecord);
        }
        return previousRecord ? [previousRecord] : false;
    }

    getNextRecords(record) {
        const { records } = this.props.list;
        const comboRecords = getComboRecords(records, record);

        const nextRecord = records[records.indexOf(record) + comboRecords.length];
        if (nextRecord?.data.product_type === 'combo'){
            return getComboRecords(records, nextRecord);
        }
        return nextRecord ? [nextRecord] : false;
    }

    canUseFormatter(column, record) {
        if (
            this.isCombo(record) &&
            this.props.aggregatedFields.includes(column.name)
        ) {
            return true;
        }
        return super.canUseFormatter(column, record);
    }

    // For totals on combo lines
    getFormattedValue(column, record) {
        if (this.isCombo(record) && this.props.aggregatedFields.includes(column.name)) {
            const total = getComboRecords(this.props.list.records, record)
                .reduce((total, record) => total + record.data[column.name], 0);

            const formatter = registry.category('formatters').get(column.fieldType, (val) => val);

            return formatter(total, {
                ...formatter.extractOptions?.(column),
                data: record.data,
                field: record.fields[column.name],
            });
        }
        return super.getFormattedValue(column, record);
    }

    isCombo(record) {
        return record.data.product_type === 'combo';
    }

    isComboItem(record) {
        return !!record.data.combo_item_id;
    }

    shouldDuplicateSectionItem(record) {
        return !this.isCombo(record) && !this.isComboItem(record);
    }

    displayDeleteIcon(record){
        return super.displayDeleteIcon(record) && !this.isComboItem(record);
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

registry.category('fields').add('sol_o2m', saleOrderLineOne2Many);
