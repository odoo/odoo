import { fields, Record } from "@mail/core/common/record";

export class ResGroups extends Record {
    static _name = "res.groups";
    static id = "id";
    /** @type {string} */
    full_name;
    partners = fields.Many("res.partner", { inverse: "group_ids" });
    privilege_id = fields.One("res.groups.privilege");
}

ResGroups.register();
