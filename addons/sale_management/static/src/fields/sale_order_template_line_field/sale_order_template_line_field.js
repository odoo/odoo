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
