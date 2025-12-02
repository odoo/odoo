import {
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
    SectionAndNoteListRenderer,
    getSectionRecords,
} from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';
import { makeContext } from '@web/core/context';
import { x2ManyCommands } from '@web/core/orm_service';
import { registry } from '@web/core/registry';

export class SaleOrderTemplateLineListRenderer extends SectionAndNoteListRenderer {
    static recordRowTemplate = 'sale_management.ListRenderer.RecordRow';

    setup() {
        super.setup();
        this.copyFields.push('is_optional');
    }

    get disableOptionalButton() {
        return this.shouldCollapse(this.record, 'is_optional');
    }

    get isCurrentSectionOptional() {
        if (this.props.list.records.length === 0) return false;

        return this.shouldCollapse(
            this.props.list.records[this.props.list.records.length - 1],
            'is_optional',
            true
        );
    }

    /**
     * Override to set the default `product_uom_qty` to 0 for new lines created under an optional
     * section.
     */
    add(params){
        params.context = this.getCreateContext(params);
        super.add(params);
    }

    getCreateContext(params) {
        const evaluatedContext = makeContext([params.context]);
        // A falsy context indicates a product line (no `display_type` specified)
        if(!evaluatedContext[`default_display_type`] && this.isCurrentSectionOptional) {
            return { ...evaluatedContext, default_product_uom_qty: 0 };
        }
        return params.context;
    }

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
    }

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (this.shouldCollapse(record, 'is_optional', true)) {
            rowClasses += ' text-primary';
        }
        return rowClasses;
    }

    async toggleIsOptional(record) {
        const setOptional = !record.data.is_optional;

        const commands = [(x2ManyCommands.update(record.resId || record._virtualId, {
            is_optional: setOptional,
        }))];

        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                changes = setOptional
                    ? { product_uom_qty: 0 }
                    : { product_uom_qty: sectionRecord.data.product_uom_qty || 1 };
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
    }

    /**
     * @override
     * Handles product line quantity adjustments when a record is dragged and dropped.
     *
     * Behavior:
     * - If a product line is moved under an optional section, its quantity is set to `0`.
     * - If a product line is dragged out of an optional section and had `0` quantity,
     *   its quantity is reset to `1`.
     * - Non-product lines (`display_type` set) are ignored.
     *
     */
    async sortDrop(dataRowId, dataGroupId, { element, previous }) {
        const record = this.props.list.records.find(r => r.id === dataRowId);
        const recordMap = this._getRecordsToRecompute(record, previous ? previous.dataset.id : null);

        await super.sortDrop(dataRowId, dataGroupId, { element, previous });

        await this._handleQuantityAdjustment(recordMap);
    }

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
    }

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
    }

}
export class SaleOrderTemplateLineOne2Many extends SectionAndNoteFieldOne2Many {
    static components = {
        ...super.components,
        ListRenderer: SaleOrderTemplateLineListRenderer,
    };
}

export const saleOrderTemplateLineOne2Many = {
    ...sectionAndNoteFieldOne2Many,
    component: SaleOrderTemplateLineOne2Many,
};

registry.category('fields').add('so_template_line_o2m', saleOrderTemplateLineOne2Many);
