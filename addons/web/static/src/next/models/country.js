import { Model } from "@web/next/model/model";
import { resCountryFields } from "./country_fields.generated";

/** @extends {Model<typeof resCountryFields>} */
export class Country extends Model {
    static _name = "res.country";
    static fields = resCountryFields;
}
