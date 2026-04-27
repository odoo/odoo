import { fields, models } from "@web/../tests/web_test_helpers";

export class BarcodeNomenclature extends models.Model {
    rule_ids = fields.One2many({ relation: "barcode.rule" });
    _records = [{ id: 1, rule_ids: [] }];
}
