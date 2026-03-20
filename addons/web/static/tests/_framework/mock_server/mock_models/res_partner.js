import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";
import * as fields from "../mock_fields";

export class ResPartner extends ServerModel {
    _name = "res.partner";

    main_user_id = fields.Many2one({ compute: "_compute_main_user_id", relation: "res.users" });

    _compute_main_user_id() {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        for (const partner of this) {
            const users = ResUsers.browse(partner.user_ids);
            const internalUsers = users.filter((user) => !user.share);
            if (internalUsers.length > 0) {
                partner.main_user_id = internalUsers[0].id;
            } else if (users.length > 0) {
                partner.main_user_id = users[0].id;
            } else {
                partner.main_user_id = false;
            }
        }
    }

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
            name: "OdooBot",
        },
    ];
}
