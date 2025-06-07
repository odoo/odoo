import { ServerModel } from "../mock_model";

export class IrModel extends ServerModel {
    _name = "ir.model";

    _records = [
        {
            id: 1,
            model: "res.partner",
            name: "Partner",
        },
    ];
}
