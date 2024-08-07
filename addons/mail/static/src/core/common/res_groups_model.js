import { Record } from "@mail/core/common/record";

export class ResGroups extends Record {
    static id = "id";
    personas = Record.many("Persona");
}

ResGroups.register();
