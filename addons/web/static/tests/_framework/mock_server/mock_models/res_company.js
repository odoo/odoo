import { serverState } from "../../mock_server_state.hoot";
import * as fields from "../mock_fields";
import { ServerModel } from "../mock_model";

export class ResCompany extends ServerModel {
    _name = "res.company";

    description = fields.Text();
    is_company = fields.Boolean({ default: false });

    _records = [
        {
            id: serverState.companyId,
            active: true,
            name: serverState.companyName,
            partner_id: serverState.companyId,
        },
    ];
}
