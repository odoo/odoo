import {
    ProductLabelSectionAndNoteListRender,
    productLabelSectionAndNoteOne2Many,
    ProductLabelSectionAndNoteOne2Many,
} from '@account/components/product_label_section_and_note_field/product_label_section_and_note_field_o2m';
import {
    SectionListRenderer,
    SectionNoteListField,
    sectionNoteListField
} from '@web/views/fields/section_note_list/section_note_list_field';
import {
    listSectionAndNoteText,
    ListSectionAndNoteText,
    sectionAndNoteFieldOne2Many,
    sectionAndNoteText,
    SectionAndNoteText,
} from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';
import { registry } from '@web/core/registry';
import { CharField } from '@web/views/fields/char/char_field';
import { ProductNameAndDescriptionListRendererMixin } from "@product/product_name_and_description/product_name_and_description";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";


export class SaleOrderLineListRenderer extends ProductLabelSectionAndNoteListRender {
    static recordRowTemplate = 'sale.ListRenderer.RecordRow';

    /**
     * Product description widget logic
     */
    getCellTitle(column, record) {
        // When using this list renderer, we don't want the product_id cell to have a tooltip with
        // its label.
        if (column.name === 'product_id' || column.name === 'product_template_id') {
            return;
        }
        super.getCellTitle(column, record);
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

    /**
     * Combo logic
     */

    /**
     * Whether the provided record is a section, a note, or a combo.
     *
     * This method's name isn't ideal since it doesn't mention combos, but we'd have to override a
     * few other methods to fix this, and the added complexity isn't worth it.
     *
     * @param record The record to check
     * @return {Boolean} Whether the record is a section, a note, or a combo.
     */
    isSectionOrNote(record=null) {
        return super.isSectionOrNote(record) || this.isCombo(record);
    }

    getRowClass(record) {
        let classNames = super.getRowClass(record);
        if (this.isCombo(record) || this.isComboItem(record)) {
            classNames = classNames.replace('o_row_draggable', '');
        }
        return `${classNames} ${this.isCombo(record) ? 'o_is_line_section' : ''}`;
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

    isCombo(record) {
        return record.data.product_type === 'combo';
    }

    isComboItem(record) {
        return !!record.data.combo_item_id;
    }
}

export class SaleSectionListRenderer extends SectionListRenderer {
    static recordRowTemplate = 'sale.SectionListRenderer.Row';

    setup() {
        super.setup();
        this.descriptionColumn = 'name';
        this.productColumns = ['product_id', 'product_template_id'];
        useEffect(
            (editedRecord) => this.focusToName(editedRecord),
            () => [this.editedRecord]
        )
    }

    focusToName(editRec) {
        if (editRec && editRec.isNew && ['line_section', 'line_note', 'line_subsection'].includes(editRec.data.display_type)) {
            const col = this.columns.find((c) => c.name === this.titleField);
            this.focusCell(col, null);
        }
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

    /**
     * Combo logic
     * 
     * This method makes delete icon invisible for combo items
     */
    displayDeleteIcon(record) {
        return !this.isComboItem(record) && super.displayDeleteIcon(record);
    }

    getRowClass(record) {
        let classNames = super.getRowClass(record);
        if (this.isCombo(record) || this.isComboItem(record)) {
            classNames = classNames.replace('o_row_draggable', '');
        }
        return `${classNames} ${this.isCombo(record) ? 'fw-bold' : ''}`;
    }

    isCellReadonly(column, record) {
        return super.isCellReadonly(column, record) || (
            this.isComboItem(record)
            && ![this.titleField, 'tax_ids', 'qty_delivered'].includes(column.name)
        );
    }

    getComboColumns(record) {
        const columns = this.getColumns(record);
        const comboColumns = columns.filter(
            (col) =>
                col.widget === "handle" ||
                (col.type === "field" && this.productColumns.includes(col.name))
        );
        return comboColumns.map((col) => {
            if (this.productColumns.includes(col.name)) {
                return { ...col, colspan: columns.length - comboColumns.length + 1 };
            } else {
                return { ...col };
            }
        });
    }

    async onDeleteRecord(record) {
        if (this.isCombo(record)) {
            await record.update({ selected_combo_items: JSON.stringify([]) });
        }
        await super.onDeleteRecord(record);
    }

    isCombo(record) {
        return record.data.product_type === 'combo';
    }

    isComboItem(record) {
        return !!record.data.combo_item_id;
    }
}

patch(SaleSectionListRenderer.prototype, ProductNameAndDescriptionListRendererMixin);

export class SaleOrderLineOne2Many extends ProductLabelSectionAndNoteOne2Many {
    static components = {
        ...ProductLabelSectionAndNoteOne2Many.components,
        ListRenderer: SaleOrderLineListRenderer,
    };
}
export class SaleSectionNoteListField extends SectionNoteListField {
    static components = {
        ...SectionNoteListField.components,
        ListRenderer: SaleSectionListRenderer,
    };
}

export const saleOrderLineOne2Many = {
    ...productLabelSectionAndNoteOne2Many,
    component: SaleOrderLineOne2Many,
    additionalClasses: sectionAndNoteFieldOne2Many.additionalClasses,
};
export const saleSectionNoteListField = {
    ...sectionNoteListField,
    component: SaleSectionNoteListField,
    additionalClasses: sectionNoteListField.additionalClasses,
};

registry.category('fields').add('sol_o2m', saleOrderLineOne2Many);
registry.category('fields').add('sale_section_note_list', saleSectionNoteListField);

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
