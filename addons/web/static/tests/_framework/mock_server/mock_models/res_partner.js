/** @odoo-module */

import { session } from "@web/session";
import { ServerModel } from "../mock_model";

export class ResPartner extends ServerModel {
    _name = "res.partner";

    _records = [
        {
            id: session.user_companies.current_company,
            active: true,
            name: session.user_companies.allowed_companies[session.user_companies.current_company]
                .name,
        },
        {
            id: session.partner_id,
            active: true,
            name: session.partner_display_name,
        },
        {
            id: session.public_partner_id,
            active: true,
            is_public: true,
            name: session.public_partner_display_name,
        },
        {
            id: session.odoobot_id,
            active: false,
            im_status: "bot",
            name: "OdooBot",
        },
    ];
}
