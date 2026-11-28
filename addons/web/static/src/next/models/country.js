import { Model } from "@web/next/store/model";
import { resCountryFields } from "./country_fields.generated";

/** @extends {Model<typeof resCountryFields>} */
export class Country extends Model {
    static _name = "res.country";
    static fields = resCountryFields;

    /** The international prefix of the phone numbers of the country: "+32". */
    get phonePrefix() {
        return this.phone_code() ? `+${this.phone_code()}` : "";
    }

    /**
     * @param {string} number a national phone number
     */
    formatPhone(number) {
        return `${this.phonePrefix} ${number.replace(/^0/, "")}`.trim();
    }
}
