/** @odoo-module */

import { session } from "@web/session";
import { ServerModel } from "../mock_model";

export class ResGroups extends ServerModel {
    _name = "res.groups";

    _records = [
        {
            id: session.group_id,
            name: "Internal User",
        },
    ];
}
