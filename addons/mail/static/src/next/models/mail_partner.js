import { Partner } from "@web/next/models/partner";
import { mailPartnerFields } from "./mail_partner_fields.generated";

/** @import { Extension } from "@web/next/model/model" */

export class MailPartner
    extends /** @type {Extension<typeof Partner, typeof mailPartnerFields>} */ (Partner)
{
    static _inherit = "res.partner";
    static fields = mailPartnerFields;
}
