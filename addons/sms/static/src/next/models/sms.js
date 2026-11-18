import { Model } from "@web/next/model/model";
import { smsSmsFields } from "./sms_fields.generated";

/** @extends {Model<typeof smsSmsFields>} */
export class Sms extends Model {
    static _name = "sms.sms";
    static fields = smsSmsFields;
}
