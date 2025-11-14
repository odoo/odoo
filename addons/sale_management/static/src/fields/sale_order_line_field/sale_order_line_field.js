import { getSectionRecords } from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';
import { SaleOrderLineListRenderer } from '@sale/js/sale_order_line_field/sale_order_line_field';
import { makeContext } from '@web/core/context';
import { x2ManyCommands } from '@web/core/orm_service';
import { patch } from '@web/core/utils/patch';

patch(SaleOrderLineListRenderer.prototype, {

    setup() {
        super.setup();
        this.copyFields.push('is_optional');
    },

    /**
     * Disable "Hide Composition" and "Hide Prices" buttons for optional sections and their
     * subsections.
     */
    get disableCompositionButton() {
        return (
            super.disableCompositionButton
            || this.shouldCollapse(this.record, 'is_optional', true)
        );
    },

    get disablePricesButton() {
        return (
            super.disablePricesButton
            || this.shouldCollapse(this.record, 'is_optional', true)
        );
    },

    /**
     * Disable "Set Optional" button if
     *  - Parent section is optional
     *  - Parent section hides prices or composition
     *  - Section itself hides prices or composition
     */
    get disableOptionalButton() {
        return (
            this.shouldCollapse(this.record, 'is_optional')
            || this.shouldCollapse(this.record, 'collapse_prices', true)
            || this.shouldCollapse(this.record, 'collapse_composition', true)
        );
    },

    get isCurrentSectionOptional() {
        if (this.props.list.records.length === 0) return false;

        return this.shouldCollapse(
            this.props.list.records[this.props.list.records.length - 1],
            'is_optional',
            true
        );
    },

    /**
     * Override to set the default `product_uom_qty` to 0 for new lines created under an optional
     * section.
     */
    add(params){
        params.context = this.getCreateContext(params);
        super.add(params);
    },

    getCreateContext(params) {
        const evaluatedContext = makeContext([params.context]);
        // A falsy context indicates a product line (no `display_type` specified)
        if(!evaluatedContext[`default_display_type`] && this.isCurrentSectionOptional) {
            return { ...evaluatedContext, default_product_uom_qty: 0 };
        }
        return params.context;
    },

    /**
     * Override to set the default `product_uom_qty` to 0 for new lines inserted by optional
     * sections from dropdown.
     */
    getInsertLineContext(record, addSubSection) {
        if (this.shouldCollapse(record, 'is_optional', true) && !addSubSection) {
            return {
                ...super.getInsertLineContext(record, addSubSection),
                default_product_uom_qty: 0
            };
        }
        return super.getInsertLineContext(record, addSubSection);
    },

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (this.shouldCollapse(record, 'is_optional', true)) {
            rowClasses += ' text-primary';
        }
        return rowClasses;
    },

    /**
     * @override
     * This override resets optional state of subsections when their parent sections is collapsed 
     */
    async toggleCollapse(record, fieldName) {
        await super.toggleCollapse(record, fieldName);

        if (this.isTopSection(record) && record.data[fieldName]) {
            const commands = [];

            for (const sectionRecord of getSectionRecords(this.props.list, record)) {
                if (this.isSubSection(sectionRecord)) {
                    commands.push(
                        x2ManyCommands.update(sectionRecord.resId || sectionRecord._virtualId, {
                            is_optional: false,
                        })
                    )
                }
            }

            if (commands.length) {
                await this.props.list.applyCommands(commands, { sort: true });
            }
        }
    },

    /**
     * Toggles optional state on a section:
     * - Product lines → qty = 0 when set optional, reset to 1 when unset.
     * - Subsections → force hide composition/prices to false.
     */
    async toggleIsOptional(record) {
        const setOptional = !record.data.is_optional;

        const commands = [(x2ManyCommands.update(record.resId || record._virtualId, {
            is_optional: setOptional,
        }))];

        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                changes = setOptional
                    ? { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }
                    : { product_uom_qty: sectionRecord.data.product_uom_qty || 1 };
            } else if (this.isSubSection(sectionRecord)) {
                changes = setOptional && {
                    collapse_composition: false,
                    collapse_prices: false,
                };
            }

            if (Object.keys(changes).length) {
                commands.push(
                    x2ManyCommands.update(
                        sectionRecord.resId || sectionRecord._virtualId,
                        changes
                    )
                );
            }
        }

        await this.props.list.applyCommands(commands, { sort: true });
    },
    /**
     * @override
     * Reset fields when a subsection is moved under an optional section,
     * since optional sections cannot contain hidden subsections or hidden prices.
     */
    resetOnResequence(record, parentSection) {
        return (
            super.resetOnResequence(record, parentSection)
            || (
                this.isSubSection(record)
                && parentSection?.data.is_optional
                && (
                    record.data.collapse_composition
                    || record.data.collapse_prices
                    || record.data.is_optional
                )
            )
        );
    },

    fieldsToReset() {
        return { ...super.fieldsToReset(), is_optional: false };
    },
});
