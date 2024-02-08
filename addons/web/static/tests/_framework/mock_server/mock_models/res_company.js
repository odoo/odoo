import { constants } from "../../test_constants.hoot";
import * as fields from "../mock_fields";
import { ServerModel } from "../mock_model";

export class ResCompany extends ServerModel {
    _name = "res.company";

    description = fields.Text();
    is_company = fields.Boolean({ default: false });

    _records = [
        {
            id: constants.COMPANY_ID,
            active: true,
            name: constants.COMPANY_NAME,
            partner_id: constants.COMPANY_ID,
        },
    ];
}
