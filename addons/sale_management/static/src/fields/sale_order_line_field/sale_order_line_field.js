import { patch } from '@web/core/utils/patch';
import { SaleOrderLineListRenderer } from '@sale/js/sale_order_line_field/sale_order_line_field';
import { x2ManyCommands } from '@web/core/orm_service';
import { getSectionRecords, getParentSectionRecord } from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';

patch(SaleOrderLineListRenderer.prototype, {

    setup() {
        super.setup();
        this.copyFields.push('is_optional');
    },

    get showOptionalButton() {
        if (this.isSubSection(this.record)) {
            const parentRecord = getParentSectionRecord(this.props.list, this.record);
            return !parentRecord?.data?.is_optional;
        }
        return true;
    },

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (record.data.is_optional || this.shouldCollapse(record, 'is_optional')) {
            rowClasses += ' text-primary';
        }
        return rowClasses;
    },

    async toggleIsOptional(record) {
        const commands = [(x2ManyCommands.update(record.resId || record._virtualId, {
            is_optional: !record.data.is_optional,
        }))];

        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            commands.push(x2ManyCommands.update(sectionRecord.resId || sectionRecord._virtualId, {
                ...(!record.data.is_optional ? {
                    product_uom_qty: 0,
                    price_total: 0,
                    price_subtotal: 0,
                } : {}),
            }));
        }

        await this.props.list.applyCommands(commands, { sort: true });
    }

});
