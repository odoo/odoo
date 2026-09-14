/** @odoo-module native */
import {
    getSectionRecords,
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
    SectionAndNoteListRenderer,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import {
    getRecordsToRecompute,
    handleQuantityAdjustment,
} from "@sale/js/section_optional_line_utils";
import { makeContext } from "@web/core/context";
import { x2ManyCommands } from "@web/core/network";
import { registry } from "@web/core/registry";
import { listId } from "@web/model/relational_model";

export class SaleOrderTemplateLineListRenderer extends SectionAndNoteListRenderer {
    static recordRowTemplate = "sale.SaleOrderTemplateLineListRenderer.RecordRow";

    setup() {
        super.setup();
        this.copyFields.push("is_optional");
    }

    disableOptionalButton(record) {
        return this.shouldCollapse(record, "is_optional");
    }

    /** @override */
    buildRowApi() {
        return {
            ...super.buildRowApi(),
            disableOptionalButton: (record) => this.disableOptionalButton(record),
            toggleIsOptional: (record) =>
                this.toggleIsOptional(this.resolveRowRecord(record)),
        };
    }

    /** @override */
    getRowProps(record, group, groupId) {
        return {
            ...super.getRowProps(record, group, groupId),
            mutedOptional: this.shouldCollapse(record, "is_optional", true),
        };
    }

    get isCurrentSectionOptional() {
        if (this.props.list.records.length === 0) {
            return false;
        }

        return this.shouldCollapse(
            this.props.list.records[this.props.list.records.length - 1],
            "is_optional",
            true,
        );
    }

    add(params) {
        params.context = this.getCreateContext(params);
        super.add(params);
    }

    getCreateContext(params) {
        const evaluatedContext = makeContext([params.context]);
        if (
            !evaluatedContext[`default_display_type`] &&
            this.isCurrentSectionOptional
        ) {
            return { ...evaluatedContext, default_product_uom_qty: 0 };
        }
        return params.context;
    }

    getInsertLineContext(record, addSubSection) {
        if (this.shouldCollapse(record, "is_optional", true) && !addSubSection) {
            return {
                ...super.getInsertLineContext(record, addSubSection),
                default_product_uom_qty: 0,
            };
        }
        return super.getInsertLineContext(record, addSubSection);
    }

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (this.shouldCollapse(record, "is_optional", true)) {
            rowClasses += " text-primary";
        }
        return rowClasses;
    }

    async toggleIsOptional(record) {
        const setOptional = !record.data.is_optional;

        const commands = [
            x2ManyCommands.update(listId(record), {
                is_optional: setOptional,
            }),
        ];

        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                changes = setOptional
                    ? { product_uom_qty: 0 }
                    : { product_uom_qty: sectionRecord.data.product_uom_qty || 1 };
            }

            if (Object.keys(changes).length) {
                commands.push(x2ManyCommands.update(listId(sectionRecord), changes));
            }
        }

        await this.props.list.applyCommands(commands, { sort: true });
    }

    /** @override */
    async sortDrop(dataRowId, dataGroupId, { element, previous }) {
        const record = this.props.list.records.find((r) => r.id === dataRowId);
        const recordMap = this._getRecordsToRecompute(
            record,
            previous ? previous.dataset.id : null,
        );

        await super.sortDrop(dataRowId, dataGroupId, { element, previous });

        await this._handleQuantityAdjustment(recordMap);
    }

    /** @see getRecordsToRecompute in section_optional_line_utils.js — shared */
    _getRecordsToRecompute(record, targetId) {
        return getRecordsToRecompute(this, record, targetId);
    }

    /** @see handleQuantityAdjustment in section_optional_line_utils.js — */
    async _handleQuantityAdjustment(recordMap) {
        return handleQuantityAdjustment(this, recordMap);
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

registry.category("fields").add("so_template_line_o2m", saleOrderTemplateLineOne2Many);
