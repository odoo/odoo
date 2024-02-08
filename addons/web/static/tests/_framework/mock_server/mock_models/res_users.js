import { constants } from "../../test_constants.hoot";
import { ServerModel } from "../mock_model";

export class ResUsers extends ServerModel {
    _name = "res.users";

    _records = [
        {
            id: constants.USER_ID,
            active: true,
            company_id: constants.COMPANY_ID,
            company_ids: [constants.COMPANY_ID],
            login: "admin",
            partner_id: constants.PARTNER_ID,
            password: "admin",
        },
        {
            id: constants.PUBLIC_USER_ID,
            active: false,
            login: "public",
            partner_id: constants.PUBLIC_PARTNER_ID,
            password: "public",
        },
    ];

    has_group() {
        return true;
    }
}
