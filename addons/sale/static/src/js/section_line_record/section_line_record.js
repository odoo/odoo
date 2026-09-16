import { Record } from "@web/model/relational_model/record";
import { hasCommonReference } from "@uom/components/many2x_uom_tags/many2x_uom_tags";
import { DISPLAY_TYPES } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";

export class SectionLineRecord extends Record {
    setup(_config, data, options = {}) {
        super.setup(_config, data, options);
        this._adjustSectionQuantities = options.adjustSectionQuantities;
    }

    async _getOnchangeValues(changes) {
        if ([DISPLAY_TYPES.SECTION, DISPLAY_TYPES.SUBSECTION].includes(this.data.display_type)) {
            if ("section_qty" in changes) {
                if (!this.data.section_qty || this.data.section_qty !== changes.section_qty) {
                    return this._adjustSectionQuantities(
                        this,
                        changes.section_qty / this.data.section_qty,
                        changes
                    );
                }
            }
            if ("section_uom_id" in changes) {
                const uoms = await this.model.orm
                    .cache({ type: "disk" })
                    .read(
                        "uom.uom",
                        [changes.section_uom_id.id, this.data.section_uom_id.id],
                        ["factor", "parent_path"]
                    );
                if (
                    ![uoms[1].factor, uoms[0].factor].includes(undefined) &&
                    hasCommonReference(uoms[0], uoms[1])
                ) {
                    return this._adjustSectionQuantities(
                        this,
                        uoms[0].factor / uoms[1].factor,
                        changes
                    );
                }
            }
        }
        return super._getOnchangeValues(changes);
    }
}
