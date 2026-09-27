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

        const linesById = {};
        const sectionLinesData = {};
        // handle section line's changes
        const commands = [x2ManyCommands.update(record.resId || record._virtualId, changes)];
        const orderChanges = {
            order_id: {
                ...this._parent._getChanges(),
                ...(!this._parent.isNew && { id: this._parent.resId }),
            },
        };

        for (const sectionLine of sectionLines) {
            const qtyField = this.isSection(sectionLine) ? "section_qty" : "product_uom_qty";
            const lineId = sectionLine.resId || sectionLine._virtualId;
            linesById[lineId] = sectionLine;
            sectionLinesData[lineId] = {
                ids: sectionLine.resId ? [sectionLine.resId] : [],
                changes: {
                    ...sectionLine._getChanges(),
                    [qtyField]: sectionLine.data[qtyField] * ratio,
                },
                changed_fields: [qtyField],
            };
            commands.push(
                x2ManyCommands.update(lineId, {
                    [qtyField]: sectionLine.data[qtyField] * ratio,
                })
            );
        }

        const fieldsSpec = getFieldsSpec(this.activeFields, this.fields, this.evalContext, {
            withInvisible: true,
        });

        const results = await this.model.orm.call("sale.order", "batch_onchange_sol", [
            sectionLinesData,
            orderChanges,
            fieldsSpec,
        ]);

        commands.push(
            ...Object.entries(results).map(([lineId, values]) => {
                const id = linesById[lineId].resId || linesById[lineId]._virtualId;
                return x2ManyCommands.update(id, values);
            })
        );

        await this._applyCommands(commands);
        return true;
    }

    shouldPropagateQuantity(line, sectionRecord) {
        return !this.isNote(line) && !this.isComboItem(line) && line !== sectionRecord;
    }
}
