import { constants } from "../../test_constants.hoot";
import { ServerModel } from "../mock_model";

export class ResPartner extends ServerModel {
    _name = "res.partner";

    _records = [
        {
            id: constants.COMPANY_ID,
            active: true,
            name: constants.COMPANY_NAME,
        },
        {
            id: constants.PARTNER_ID,
            active: true,
            name: constants.PARTNER_NAME,
        },
        {
            id: constants.PUBLIC_PARTNER_ID,
            active: true,
            is_public: true,
            name: constants.PUBLIC_PARTNER_NAME,
        },
        {
            id: constants.ODOOBOT_ID,
            active: false,
            im_status: "bot",
            name: "OdooBot",
        },
    ];
}
