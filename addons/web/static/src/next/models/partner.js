import { Model } from "@web/next/model/model";
import { resPartnerFields } from "./partner_fields.generated";

/** @extends {Model<typeof resPartnerFields>} */
export class Partner extends Model {
    static _name = "res.partner";
    static fields = resPartnerFields;
}
