import {
    getSectionRecords,
    DISPLAY_TYPES,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { SectionLineRecord } from "@sale/js/section_line_record/section_line_record";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { StaticList } from "@web/model/relational_model/static_list";
import { getFieldsSpec } from "@web/model/relational_model/utils";

export class SaleOrderFormStaticList extends StaticList {
    _buildRecord(config, data, options) {
        if (this.resModel === "sale.order.line") {
            options.adjustSectionQuantities = this.adjustSectionQuantities.bind(this);
            return new SectionLineRecord(this.model, config, data, options);
        }
        return super._buildRecord(config, data, options);
    }

    isSection(record) {
        return [DISPLAY_TYPES.SECTION, DISPLAY_TYPES.SUBSECTION].includes(record.data.display_type);
    }

    isNote(record) {
        return record.data.display_type === DISPLAY_TYPES.NOTE;
    }

    isSubsection(record) {
        return record.data.display_type === DISPLAY_TYPES.SUBSECTION;
    }

    isComboItem(record) {
        return !!record.data.combo_item_id;
    }

    async adjustSectionQuantities(record, ratio, changes) {
        if (ratio === 1) {
            return false;
        }

        const sectionLines = getSectionRecords(this, record, this.isSubsection(record)).filter(
            (line) => this.shouldPropagateQuantity(line, record)
        );

        if (!sectionLines.length) {
            return false;
        }

        const commands = [x2ManyCommands.update(record.resId || record._virtualId, changes)];

        const recordsList = sectionLines.map((sectionLine) => {
            const qtyField = this.isSection(sectionLine) ? "section_qty" : "product_uom_qty";
            const id = sectionLine.resId || sectionLine._virtualId;

            const lineChanges = {
                ...sectionLine._getChanges(),
                order_id: {
                    ...this._parent._getChanges(),
                    ...(!this._parent.isNew && { id: this._parent.resId }),
                },
                [qtyField]: sectionLine.data[qtyField] * ratio,
            };

            // update the line's quantity field
            commands.push(x2ManyCommands.update(id, { [qtyField]: lineChanges[qtyField] }));

            return {
                id: sectionLine.resId || false,
                changes: lineChanges,
                field_names: [qtyField],
                virtual_id: sectionLine._virtualId,
            };
        });

        const fieldsSpec = getFieldsSpec(this.activeFields, this.fields, this.evalContext, {
            withInvisible: true,
        });

        const responses = await this.model.orm.call("sale.order.line", "onchange_batch", [
            recordsList,
            fieldsSpec,
        ]);

        for (const { id, virtual_id, result } of responses) {
            if (result.warning) {
                this.model._displayOnchangeWarning(result.warning);
            }

            const lineId = id || virtual_id;
            const values = result.value;

            if (values) {
                commands.push(x2ManyCommands.update(lineId, values));
            }
        }

        await this._applyCommands(commands);
        return true;
    }

    shouldPropagateQuantity(line, sectionRecord) {
        return !this.isNote(line) && !this.isComboItem(line) && line !== sectionRecord;
    }
}
