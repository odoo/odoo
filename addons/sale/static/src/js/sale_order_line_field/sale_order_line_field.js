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
import { getRecordsUntilSection } from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';

function getParentSection(list, record) {
    const { parent } = getRecordsUntilSection(list, record, false, true).sectionRecords[0];
    return parent;
}

export class SaleOrderLineListRenderer extends ProductLabelSectionAndNoteListRender {
    static recordRowTemplate = 'sale.ListRenderer.RecordRow';

    setup() {
        super.setup();
        this.pricesColumns = ['price_unit', 'price_subtotal', 'price_total', 'discount'];
    }

    parentSection(record, isSubSection= false) {
        return getParentSection(this.props.list, record);
    }

    _papaSaysHide(record, key) {
        if (this.isTopSection(record)) {
            return false;
        }

        if ((tish.isSection(record) && !this.isTopSection(record)) && !this) {
            return hierarchyItem.parent?.record.data[key];
        }

        if (hierarchyItem.isRecord || hierarchyItem.isNote) {
            const parent = hierarchyItem.parent;
            if (!parent || parent.isRoot) return false;

            if (parent.isTopSection) {
                return parent.record.data[key];
            }

            if (parent.isSubSection) {
                return parent.parent.isTopSection
                    ? parent.parent.record.data[key] || parent.record.data[key]
                    : parent.record.data[key];
            }
        }

        return false;
    }

    getDropDownItems(record) {
        return [
            {
                id: "toggleComposition",
                label: record.data.hide_composition ? _t("Show Composition") : _t("Hide Composition"),
                icon: record.data.hide_composition ? "fa-eye" : "fa-eye-slash",
                onSelected: async () => {
                    const changes = { hide_composition: !hierarchyItem.record.data.hide_composition };
                    await hierarchyItem.record.update(changes);
                },
            },
            {
                id: "togglePrices",
                label: record.data.hide_prices ? _t("Show Prices") : _t("Hide Prices"),
                icon: record.data.hide_prices ? "fa-eye" : "fa-eye-slash",
                onSelected: async () => {
                    const changes = { hide_prices: !record.data.hide_prices };
                    await record.update(changes);
                },
            },
        ];
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
