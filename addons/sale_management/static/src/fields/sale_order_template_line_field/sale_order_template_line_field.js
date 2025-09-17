import {
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
    SectionAndNoteListRenderer,
    getSectionRecords,
    getParentSectionRecord,
} from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';
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

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (this.shouldCollapse(record, 'is_optional', true)) {
            rowClasses += ' text-primary';
        }
        return rowClasses;
    }

    async toggleIsOptional(record) {
        const commands = [(x2ManyCommands.update(record.resId || record._virtualId, {
            is_optional: !record.data.is_optional,
        }))];

        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                changes = !record.data.is_optional
                    ? { product_uom_qty: 0 }
                    : { product_uom_qty: sectionRecord.data.product_uom_qty || 1 };
            }

            commands.push(
                x2ManyCommands.update(
                    sectionRecord.resId || sectionRecord._virtualId,
                    changes
                )
            );
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
    async sortDrop(dataRowId, dataGroupId, options) {
        const record = this.props.list.records.find(r => r.id === dataRowId);
        const oldParentSection = getParentSectionRecord(this.props.list, record);
        const wasOptional = this.shouldCollapse(record, 'is_optional');

        await super.sortDrop(dataRowId, dataGroupId, options);

        const newParentSection = getParentSectionRecord(this.props.list, record);
        if (oldParentSection === newParentSection || record.data.display_type) return;

        let newProductQty = null;

        if (this.shouldCollapse(record, 'is_optional')) {
            newProductQty = 0;
        } else if (wasOptional && !record.data.product_uom_qty) {
            newProductQty = 1;
        }

        if (newProductQty !== null) {
            await record.update({ product_uom_qty: newProductQty });
        }
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
