import { Model } from "@web/next/model/model";
import { mailActivityFields } from "./activity_fields.generated";

/** @extends {Model<typeof mailActivityFields>} */
export class Activity extends Model {
    static _name = "mail.activity";
    static fields = mailActivityFields;
}
