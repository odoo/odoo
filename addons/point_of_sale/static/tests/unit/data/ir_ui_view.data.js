import { models } from "@web/../tests/web_test_helpers";

export class IrUiView extends models.ServerModel {
    _name = "ir.ui.view";

    _load_pos_data_fields() {
        return ["id", "key"];
    }
}
