import { Model } from "@web/next/model/model";
import { resUsersFields } from "./user_fields.generated";

/** @extends {Model<typeof resUsersFields>} */
export class User extends Model {
    static _name = "res.users";
    static fields = resUsersFields;
}
