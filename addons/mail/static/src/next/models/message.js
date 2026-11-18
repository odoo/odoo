import { Model } from "@web/next/model/model";
import { mailMessageFields } from "./message_fields.generated";

/** @extends {Model<typeof mailMessageFields>} */
export class Message extends Model {
    static _name = "mail.message";
    static fields = mailMessageFields;
}
