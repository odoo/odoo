import { Model } from "@web/next/store/model";
import { resUsersFields } from "./user_fields.generated";

/** @extends {Model<typeof resUsersFields>} */
export class User extends Model {
    static _name = "res.users";
    static fields = resUsersFields;

    /** An internal user, as opposed to a portal or public one. */
    get isInternal() {
        return this.active() && !this.share();
    }

    /** The name of the user, or their login as a fallback. */
    get displayName() {
        return this.partner_id()?.name() || this.name() || this.login() || "";
    }
}
