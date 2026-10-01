import { models } from "@web/../tests/web_test_helpers";

export class UomUom extends models.ServerModel {
    _name = "uom.uom";

    _records = [
        { id: 1, name: "Units", factor: 1, parent_path: "1/" },
        { id: 2, name: "Dozens", factor: 12, parent_path: "1/2/" },
        { id: 3, name: "kg", factor: 1, parent_path: "3/" },
    ];
}
