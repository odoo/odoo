import { fields, Record } from "@mail/core/common/record";

export class ResGroups extends Record {
    static _name = "res.groups";
    static id = "id";
    /** @type {string} */
    full_name;
    partner_ids = fields.Many("res.partner");
    privilege_id = fields.One("res.groups.privilege");
}

ResGroups.register();
