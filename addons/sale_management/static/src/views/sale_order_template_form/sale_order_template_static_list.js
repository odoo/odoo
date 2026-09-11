import {
    getSectionRecords,
    DISPLAY_TYPES,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { SectionLineRecord } from "@sale/js/section_line_record/section_line_record";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { StaticList } from "@web/model/relational_model/static_list";

export class SaleOrderTemplateFormStaticList extends StaticList {
    _buildRecord(config, data, options) {
        if (this.resModel === "sale.order.template.line") {
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

    async adjustSectionQuantities(record, ratio, changes) {
        if (ratio === 1) {
            return false;
        }

        const sectionLines = getSectionRecords(this, record, this.isSubsection(record)).filter(
            (line) => !this.isNote(line) && line !== record
        );

        if (!sectionLines.length) {
            return false;
        }

        // handle section line's changes
        const commands = [x2ManyCommands.update(record.resId || record._virtualId, changes)];

        for (const sectionLine of sectionLines) {
            const qtyField = this.isSection(sectionLine) ? "section_qty" : "product_uom_qty";
            commands.push(
                x2ManyCommands.update(sectionLine.resId || sectionLine._virtualId, {
                    [qtyField]: sectionLine.data[qtyField] * ratio,
                })
            );
        }

        await this._applyCommands(commands);
        return false;
    }
}
