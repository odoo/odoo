import { patch } from '@web/core/utils/patch';
import { SaleOrderLineListRenderer } from '@sale/js/sale_order_line_field/sale_order_line_field';
import { x2ManyCommands } from '@web/core/orm_service';
import { getSectionRecords, getParentSectionRecord } from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';

patch(SaleOrderLineListRenderer.prototype, {

    setup() {
        super.setup();
        this.copyFields.push('is_optional');
    },

    /**
     * Disable "Hide Composition" and "Hide Prices" buttons for optional sections and their subsections.
     */
    get disableCompositionButton() {
        return (
            super.disableCompositionButton
            || this.record.data.is_optional
            || this.shouldCollapse(this.record, 'is_optional')
        );
    },

    get disablePricesButton() {
        return (
            super.disablePricesButton
            || this.record.data.is_optional
            || this.shouldCollapse(this.record, 'is_optional')
        );
    },

    get disableOptionalButton() {
        return (
            this.shouldCollapse(this.record, 'is_optional')
            || this.shouldCollapse(this.record, 'collapse_prices')
            || this.shouldCollapse(this.record, 'collapse_composition')
            || this.hidePrices
            || this.hideComposition
        );
    },

    /**
     * Hidden section or Hidden prices sections can't be optional
     */
    get showOptionalButton() {
        return !( this.record.data.collapse_composition || this.record.data.collapse_prices );
    },

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (record.data.is_optional || this.shouldCollapse(record, 'is_optional')) {
            rowClasses += ' text-primary';
        }
        return rowClasses;
    },

    /**
     * Toggles optional state on a section:
     * - Product lines → qty = 0 when set optional, reset to 1 when unset.
     * - Subsections → force hide composition/prices to false.
     */
    async toggleIsOptional(record) {
        const commands = [(x2ManyCommands.update(record.resId || record._virtualId, {
            is_optional: !record.data.is_optional
        }))];

        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                changes = !record.data.is_optional
                    ? { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }
                    : { product_uom_qty: sectionRecord.data.product_uom_qty || 1 };
            } else if (this.isSubSection(sectionRecord)) {
                changes = !record.data.is_optional && {
                    collapse_composition: false,
                    collapse_prices: false,
                };
            }

            commands.push(
                x2ManyCommands.update(
                    sectionRecord.resId || sectionRecord._virtualId,
                    changes
                )
            );
        }

        await this.props.list.applyCommands(commands, { sort: true });
    },

    /**
     * @override
     * Handles product line quantity adjustments when a record is dragged and dropped.
     *
     * Behavior:
     * - If a product line is moved under an optional section, its quantity is set to `0`.
     * - If a product line is dragged out of an optional section and had `0` quantity,
     *   its quantity is reset to `1`.
     * - Non-product lines (`display_type` set) are ignored.
     */
    async sortDrop(dataRowId, dataGroupId, options) {
        const record = this.props.list.records.find(r => r.id === dataRowId);
        const oldParent = getParentSectionRecord(this.props.list, record);
        const wasOptional = this.shouldCollapse(record, 'is_optional');

        await super.sortDrop(dataRowId, dataGroupId, options);

        const newParent = getParentSectionRecord(this.props.list, record);
        if (oldParent === newParent) return;

        let newProductQty = null;

        if (this.shouldCollapse(record, 'is_optional')) {
            newProductQty = 0;
        } else if (wasOptional && !record.data.product_uom_qty) {
            newProductQty = 1;
        }

        if (newProductQty !== null && !record.data.display_type) {
            await record.update({ product_uom_qty: newProductQty });
        }
    },

    /**
     * @override
     * Reset fields when a subsection is moved under an optional section,
     * since optional sections cannot contain hidden subsections or hidden prices.
     */
    resetOnResequence(record, parentSection) {
        if (this.isSubSection(record)) {
            return (
                record.data.collapse_composition
                || record.data.collapse_prices
                || record.data.is_optional
            ) && (
                parentSection.data.collapse_composition
                || parentSection.data.is_optional
            );
        }
        return super.resetOnResequence(record, parentSection);
    },

    fieldsToReset() {
        return { ...super.fieldsToReset(), is_optional: false };
    },
});
