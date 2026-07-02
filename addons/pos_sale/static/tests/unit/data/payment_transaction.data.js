import { patch } from "@web/core/utils/patch";
import { models } from "@web/../tests/web_test_helpers";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

export class PaymentTransaction extends models.ServerModel {
    _name = "payment.transaction";

    _load_pos_data_fields() {
        return ["amount", "payment_id"];
    }

    _records = [];
}

patch(hootPosModels, [...hootPosModels, PaymentTransaction]);
