import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";

export class ResPartner extends ServerModel {
    _name = "res.partner";

    _records = [
        {
            id: serverState.companyId,
            active: true,
            name: serverState.companyName,
        },
        {
            id: serverState.partnerId,
            active: true,
            name: serverState.partnerName,
        },
        {
            id: serverState.publicPartnerId,
            active: true,
            is_public: true,
            name: serverState.publicPartnerName,
        },
        {
            id: serverState.odoobotId,
            active: false,
            im_status: "bot",
            name: "OdooBot",
        },
    ];
}
