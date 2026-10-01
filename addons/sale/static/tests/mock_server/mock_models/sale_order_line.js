import { fields, models } from "@web/../tests/web_test_helpers";

export class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    label = fields.Text({ compute: "_computeLabel", readonly: false });
    section_qty = fields.Float({ compute: "_computeSectionQtyUom", readonly: false });
    section_uom_id = fields.Many2one({
        relation: "uom.uom",
        compute: "_computeSectionQtyUom",
        readonly: false,
    });

    // directly set `name` to `label` to avoid complications with `display_name`
    _computeLabel() {
        for (const record of this) {
            record.label = record.name;
        }
    }

    // sections default to 1 Unit, while values set by a test or saved by the user are kept
    _computeSectionQtyUom() {
        for (const record of this) {
            if (["line_section", "line_subsection"].includes(record.display_type)) {
                record.section_qty ||= 1;
                record.section_uom_id ||= 1;
            }
        }
    }
}
