import { patch } from "@web/core/utils/patch";
import { models } from "@web/../tests/web_test_helpers";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

export class AccountPayment extends models.ServerModel {
    _name = "account.payment";

    _load_pos_data_fields() {
        return ["name", "move_id"];
    }

    _records = [];
}

patch(hootPosModels, [...hootPosModels, AccountPayment]);
