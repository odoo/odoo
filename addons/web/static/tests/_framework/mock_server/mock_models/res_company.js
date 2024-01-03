/** @odoo-module */

import { session } from "@web/session";
import { ServerModel } from "../mock_model";
import * as fields from "../mock_fields";

export class ResCompany extends ServerModel {
    _name = "res.company";

    description = fields.Text();
    is_company = fields.Boolean({ default: false });

    _records = Object.values(session.user_companies.allowed_companies).map((companyDef) => ({
        ...companyDef,
        active: true,
        partner_id: companyDef.id,
    }));
}
