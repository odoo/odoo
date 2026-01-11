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

        const proms = [];
        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                if (setOptional) {
                    changes = { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }
                } else {
                    proms.push(sectionRecord._update({ product_uom_qty: sectionRecord.data.product_uom_qty || 1 }));
                }
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
        await Promise.all(proms);
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
    async sortDrop(dataRowId, dataGroupId, { element, previous }) {
        const record = this.props.list.records.find(r => r.id === dataRowId);
        const recordMap = this._getRecordsToRecompute(record, previous ? previous.dataset.id : null);

        await super.sortDrop(dataRowId, dataGroupId, { element, previous });

        await this._handleQuantityAdjustment(recordMap);
    },

    /**
     * Builds a map of records whose optional state needs to be recomputed
     * after a record is moved within the list.
     *
     * The map’s keys are record IDs, and values represent their current
     * `is_optional` collapse state as determined by `shouldCollapse()`.
     *
     * @param {Object} record - The record being moved.
     * @param {number|string} targetId - The ID of the record that serves as the new drop target.
     * @returns {Map<number|string, boolean>} A map of record IDs to their recomputed optional states.
     */
    _getRecordsToRecompute(record, targetId) {
        const optionalStateMap = new Map();

        if (this.isSection(record)) { // If a section or subsection is moved
            let currentIndex = this.props.list.records.indexOf(record);
            let targetIndex = this.props.list.records.findIndex(r => r.id === targetId);
            if (currentIndex > targetIndex) {
                //When moving up, recompute:
                // 1. All records under the moved section.
                // 2. All records between the new and old positions.
                for (let i = currentIndex; i > targetIndex; i--) {
                    if (!this.props.list.records[i].data.display_type) {
                        optionalStateMap.set(
                            this.props.list.records[i].id,
                            this.shouldCollapse(this.props.list.records[i], 'is_optional')
                        );
                    }
                }
                for (const sectionRecord of getSectionRecords(this.props.list, record)) {
                    if (!sectionRecord.data.display_type) {
                        optionalStateMap.set(sectionRecord.id, this.shouldCollapse(sectionRecord, 'is_optional'));
                    }
                }
            } else {
                //When moving down, recompute:
                // 1. All records under sections between the old and new positions.
                // 2. All records between the old and new positions (skipping overlaps).
                for (let i = currentIndex; i <= targetIndex; i++) {
                    if (this.isSection(this.props.list.records[i])) {
                        for (const sectionRecord of getSectionRecords(this.props.list, this.props.list.records[i])) {
                            if (
                                !optionalStateMap.has(sectionRecord.id)
                                && !sectionRecord.data.display_type
                            ) {
                                optionalStateMap.set(
                                    sectionRecord.id,
                                    this.shouldCollapse(sectionRecord, 'is_optional')
                                );
                            }
                        }
                    }

                    // we must skip overlapping records
                    if (
                        !optionalStateMap.has(this.props.list.records[i].id)
                        && !this.props.list.records[i].data.display_type
                    ) {
                        optionalStateMap.set(
                            this.props.list.records[i].id,
                            this.shouldCollapse(this.props.list.records[i], 'is_optional')
                        );
                    }
                }
            }
        } else if (!record.data.display_type) { // If a regular record is moved compute its own optional state
            optionalStateMap.set(record.id, this.shouldCollapse(record, 'is_optional'));
        }

        return optionalStateMap;
    },

    async _handleQuantityAdjustment(recordMap) {
        const commands = [];

        for (const [recordId, wasOptional] of recordMap.entries()) {
            const record = this.props.list.records.find(r => r.id === recordId);
            const isOptional = this.shouldCollapse(record, 'is_optional');

            if (wasOptional && !isOptional && !record.data.product_uom_qty) {
                commands.push(x2ManyCommands.update(
                    record.resId || record._virtualId, { product_uom_qty: 1 }
                ));
            } else if (!wasOptional && isOptional) {
                commands.push(x2ManyCommands.update(
                    record.resId || record._virtualId, { product_uom_qty: 0 }
                ));
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

    async moveCombo(record, direction) {
        const wasOptional = this.shouldCollapse(record, 'is_optional');

        await super.moveCombo(record, direction);

        const isOptional = this.shouldCollapse(record, 'is_optional');

        if (wasOptional && !isOptional && !record.data.product_uom_qty) {
            await record.update({ product_uom_qty: 1 });
        } else if (!wasOptional && isOptional) {
            await record.update({ product_uom_qty: 0 });
        }
    }
});
