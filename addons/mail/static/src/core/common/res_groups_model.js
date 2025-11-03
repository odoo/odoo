import { fields, Record } from "@mail/model/export";

export class ResGroups extends Record {
    static _name = "res.groups";
    static id = "id";
    /** @type {string} */
    full_name;
    /** @type {number} */
    id;
    partners = fields.Many("res.partner", { inverse: "group_ids" });
    privilege_id = fields.One("res.groups.privilege");
}

ResGroups.register();
