import { getSectionRecords } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { SaleOrderLineRecord } from "@sale/js/sale_order_line_record/sale_order_line_record";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { StaticList } from "@web/model/relational_model/static_list";
import { getFieldsSpec } from "@web/model/relational_model/utils";

export class SaleOrderFormStaticList extends StaticList {
    getRecordClass() {
        if (this.resModel === "sale.order.line") {
            return SaleOrderLineRecord;
        }
        return super.getRecordClass();
    }

    isSection(record) {
        return (
            record.data.display_type === "line_section" ||
            record.data.display_type === "line_subsection"
        );
    }

    isNote(record) {
        return record.data.display_type === "line_note";
    }

    isSubsection(record) {
        return record.data.display_type === "line_subsection";
    }

    isComboItem(record) {
        return !!record.data.combo_item_id;
    }

    async adjustSectionQuantities(record, ratio, changes) {
        if (ratio === 1) {
            return;
        }

        const sectionLines = getSectionRecords(this, record, this.isSubSection(record)).filter(
            (line) => !this.isNote(line) && !this.isComboItem(line) && line !== record
        );

        if (!sectionLines.length) {
            return;
        }

        const linesById = {};
        const sectionLinesData = {};
        const commands = [];
        const orderChanges = {
            order_id: {
                ...(await this._parent.getChanges()),
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
                    ...(await sectionLine.getChanges({ withReadonly: true })),
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

        const results = await this.orm.call("sale.order", "batch_onchange_sol", [
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

        await this.applyCommands(commands);
    }
}
