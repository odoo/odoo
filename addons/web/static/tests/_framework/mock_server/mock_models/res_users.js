/** @odoo-module */

import { session } from "@web/session";
import { ServerModel } from "../mock_model";

export class ResUsers extends ServerModel {
    _name = "res.users";

    _records = [
        {
            id: session.uid,
            active: true,
            company_id: session.user_companies.current_company,
            company_ids: Object.keys(session.user_companies.allowed_companies).map(Number),
            login: "admin",
            partner_id: session.partner_id,
            password: "admin",
        },
        {
            id: session.public_user_id,
            active: false,
            login: "public",
            partner_id: session.public_partner_id,
            password: "public",
        },
    ];

    has_group() {
        return true;
    }
}
