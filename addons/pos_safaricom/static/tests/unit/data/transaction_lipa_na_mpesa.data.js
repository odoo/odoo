import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class TransactionLipaNaMpesa extends models.ServerModel {
    _name = "transaction.lipa.na.mpesa";

    _records = [
        {
            id: 1,
            trans_id: "QWE123",
            name: "A Test Customer",
            number: "254712345678",
            amount: 10,
            received_at: "2025-07-03 17:04:14",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, TransactionLipaNaMpesa]);
