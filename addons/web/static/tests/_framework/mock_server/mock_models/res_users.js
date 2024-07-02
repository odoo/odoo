import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";

export class ResUsers extends ServerModel {
    _name = "res.users";

    _records = [
        {
            id: serverState.userId,
            active: true,
            company_id: serverState.companies[0]?.id,
            company_ids: serverState.companies.map((company) => company.id),
            login: "admin",
            partner_id: serverState.partnerId,
            password: "admin",
        },
        {
            id: serverState.publicUserId,
            active: false,
            login: "public",
            partner_id: serverState.publicPartnerId,
            password: "public",
        },
    ];

    has_group() {
        return true;
    }

    _is_public(id) {
        return id === serverState.publicUserId;
    }

    /**
     * @override
     * @type {ServerModel["create"]}
     */
    create() {
        const userId = super.create(...arguments);
        const [user] = this.env["res.users"].browse(userId);
        if (user && !user.partner_id) {
            this.env["res.users"].write(userId, { partner_id: this.env["res.partner"].create({}) });
        }
        return userId;
    }
}
