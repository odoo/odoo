import {
    ProductLabelSectionAndNoteListRender,
    productLabelSectionAndNoteOne2Many,
    ProductLabelSectionAndNoteOne2Many,
} from '@account/components/product_label_section_and_note_field/product_label_section_and_note_field_o2m';
import {
    listSectionAndNoteText,
    ListSectionAndNoteText,
    sectionAndNoteFieldOne2Many,
    sectionAndNoteText,
    SectionAndNoteText,
} from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';
import { registry } from '@web/core/registry';
import { CharField } from '@web/views/fields/char/char_field';

function getComboRecords(listRecords, record) {
    const comboRecords = [];

    if (record.data.product_type === 'combo') {
        // if currernt record is combo then we move forward util we find non combo line
        comboRecords.push(record);
        let index = listRecords.indexOf(record) + 1;

        while (index < listRecords.length) {
            const r = listRecords[index];
            if (!r.data.combo_item_id?.id || r.data.linked_line_id?.id !== record.resId) {
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

            if (r.data.product_type === 'combo' && r.resId === record.data.linked_line_id?.id) {
                break;
            }
            index--;
        }
    }

    return comboRecords;
}

export class SaleOrderLineListRenderer extends ProductLabelSectionAndNoteListRender {
    static recordRowTemplate = 'sale.ListRenderer.RecordRow';

    setup(){
        super.setup();
        this.priceColumns.push('discount');
    }

    /**
     * Little hack to make sure we get correct title field everytime
     * while accessing comboColumns
     */
    get comboColumns() {
        return [this.titleField, ...this.props.aggregatedFields, 'product_uom_qty', 'discount'];
    }

    /**
     * Product description widget logic
     */
    getCellTitle(column, record) {
        // When using this list renderer, we don't want the product_id cell to have a tooltip with
        // its label.
        if (column.name === 'product_id' || column.name === 'product_template_id') {
            return;
        }
        return super.getCellTitle(column, record);
    }

    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        let productTmplCol = activeColumns.find((col) => col.name === 'product_template_id');
        let productCol = activeColumns.find((col) => col.name === 'product_id');

        if (productCol && productTmplCol) {
            // Hide the template column if the variant one is enabled.
            activeColumns = activeColumns.filter((col) => col.name != 'product_template_id')
        }

        return activeColumns;
    }

    getRowClass(record) {
        let classNames = super.getRowClass(record);
        if (this.isCombo(record) || this.isComboItem(record)) {
            classNames = classNames.replace('o_row_draggable', '');
        }
        return `${classNames} ${this.isCombo(record) ? 'o_is_line_section o_is_line_section_no_indent' : ''}`;
    }

    isCellReadonly(column, record) {
        return super.isCellReadonly(column, record) || (
            this.isComboItem(record)
                && ![this.titleField, 'tax_ids', 'qty_delivered'].includes(column.name)
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

export class SaleOrderLineText extends SectionAndNoteText {
    get componentToUse() {
        return this.props.record.data.product_type === 'combo' ? CharField : super.componentToUse;
    }
}

export class ListSaleOrderLineText extends ListSectionAndNoteText {
    get componentToUse() {
        return this.props.record.data.product_type === 'combo' ? CharField : super.componentToUse;
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

registry.category('fields').add('sol_text', saleOrderLineText);
registry.category('fields').add('list.sol_text', listSaleOrderLineText);
