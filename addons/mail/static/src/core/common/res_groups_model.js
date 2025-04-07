import { fields, Record } from "@mail/core/common/record";

export class ResGroups extends Record {
    static _name = "res.groups";
    static id = "id";
    personas = fields.Many("Persona");
}

ResGroups.register();
