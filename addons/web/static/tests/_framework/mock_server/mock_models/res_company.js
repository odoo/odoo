import { serverState } from "../../mock_server_state.hoot";
import * as fields from "../mock_fields";
import { ServerModel } from "../mock_model";

export class ResCompany extends ServerModel {
    _name = "res.company";

    description = fields.Text();
    is_company = fields.Boolean({ default: false });

    _records = serverState.companies.map((company) => ({
        id: company.id,
        active: true,
        name: company.name,
        partner_id: company.id,
    }));
}
