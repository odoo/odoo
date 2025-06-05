import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";

export class ResPartner extends ServerModel {
    _name = "res.partner";

    _records = [
        ...serverState.companies.map((company) => ({
            id: company.id,
            active: true,
            name: company.name,
        })),
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
