import { computed } from "@odoo/owl";
import { Model } from "@web/next/store/model";
import { resPartnerFields } from "./partner_fields.generated";

/** @extends {Model<typeof resPartnerFields>} */
export class Partner extends Model {
    static _name = "res.partner";
    static fields = resPartnerFields;

    /** The name, with the code of the country if any: "Alice (BE)". */
    label = computed(() => {
        const code = this.country_id()?.code();
        return code ? `${this.name()} (${code})` : this.name() || "";
    });

    /** The company this partner belongs to, or the partner itself. */
    get commercialPartner() {
        /** @type {Partner} */
        let partner = this;
        for (let parent = partner.parent_id(); parent; parent = partner.parent_id()) {
            if (partner.is_company()) {
                break;
            }
            partner = parent;
        }
        return partner;
    }

    get contacts() {
        return this.child_ids().filter((child) => child.active() && !child.is_company());
    }

    get isInternalUser() {
        return this.user_ids().some((user) => user.isInternal);
    }

    get canBeEmailed() {
        return Boolean(this.email());
    }

    /**
     * @param {Partner} other
     */
    isInSameCompany(other) {
        return this.commercialPartner === other.commercialPartner;
    }

    /** Archives the partner, and its contacts with it. */
    archive() {
        this.active.set(false);
        for (const contact of this.contacts) {
            contact.archive();
        }
    }
}
