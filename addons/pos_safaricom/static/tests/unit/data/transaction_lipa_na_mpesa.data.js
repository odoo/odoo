import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class TransactionLipaNaMpesa extends models.ServerModel {
    _name = "transaction.lipa.na.mpesa";

    _records = [
        {
            id: 1,
            name: "QWE123",
            number: "254712345678",
            amount: 15,
            received_at: "2026-04-10 10:00:00",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, TransactionLipaNaMpesa]);
