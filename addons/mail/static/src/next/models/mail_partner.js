import { Partner } from "@web/next/models/partner";
import { mailPartnerFields } from "./mail_partner_fields.generated";

/** @import { Extension } from "@web/next/store/model" */

export class MailPartner
    extends /** @type {Extension<typeof Partner, typeof mailPartnerFields>} */ (Partner)
{
    static _inherit = "res.partner";
    static fields = mailPartnerFields;

    /** A blacklisted partner has an email, but does not want any. */
    get canBeEmailed() {
        return super.canBeEmailed && !this.is_blacklisted();
    }

    get overdueActivities() {
        return this.activity_ids().filter((activity) => activity.isOverdue);
    }

    /** The most recent message posted on the partner, if any. */
    get lastMessage() {
        return this.message_ids().reduce(
            (last, message) =>
                !last || String(message.date()) > String(last.date()) ? message : last,
            /** @type {import("./message").Message | null} */ (null)
        );
    }

    /** The other partners who follow this one. */
    get followers() {
        return this.message_partner_ids().filter((partner) => partner !== this);
    }
}
