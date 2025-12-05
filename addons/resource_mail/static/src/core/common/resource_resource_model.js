import { fields, Record } from "@mail/model/export";

export class ResourceResource extends Record {
    static _name = "resource.resource";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {'user'|'material'} */
    resource_type = "user";
    user_id = fields.One("res.users");
}

ResourceResource.register();
