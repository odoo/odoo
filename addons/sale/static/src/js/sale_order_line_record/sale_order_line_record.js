import { Record } from "@web/model/relational_model/record";
import { hasCommonReference } from "@uom/components/many2x_uom_tags/many2x_uom_tags";

export class SaleOrderLineRecord extends Record {
    async _getOnchangeValues(changes) {
        if (
            "section_qty" in changes &&
            ["line_section", "line_subsection"].includes(this.data.display_type)
        ) {
            if (!this.data.section_qty || this.data.section_qty !== changes.section_qty) {
                return this.env.adjustSectionQuantities(
                    this,
                    changes.section_qty / this.data.section_qty,
                    changes
                );
            }
        }
        if (
            "section_uom_id" in changes &&
            ["line_section", "line_subsection"].includes(this.data.display_type)
        ) {
            const uoms = await this.model.orm
                .cache({ type: "disk" })
                .read(
                    "uom.uom",
                    [changes.section_uom_id.id, this.data.section_uom_id.id],
                    ["name", "factor", "parent_path"]
                );
            if (!uoms[1].factor || !hasCommonReference(uoms[0], uoms[1])) {
                return this.env.adjustSectionQuantities(
                    this,
                    uoms[0].factor / uoms[1].factor,
                    changes
                );
            }
        }
        return super._getOnchangeValues(changes);
    }
}
