import { parseEmail } from "@mail/utils/common/format";
import { fields, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class ResFake extends models.Model {
    _name = "res.fake";
    _primary_email = "email_cc";

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <field name="name"/>
                    <field name="partner_id" />
                    <field name="email_cc" />
                </sheet>
                <chatter/>
            </form>`,
    };

    name = fields.Char({ string: "Name" });
    activity_ids = fields.One2many({ relation: "mail.activity", string: "Activities" });
    email_from = fields.Char({ string: "Email" });
    email_cc = fields.Char();
    message_ids = fields.One2many({ relation: "mail.message" });
    message_follower_ids = fields.Many2many({ relation: "mail.followers", string: "Followers" });
    partner_ids = fields.One2many({ relation: "res.partner", string: "Related partners" });
    phone = fields.Char({ string: "Phone number" });
    partner_id = fields.Many2one({ relation: "res.partner", string: "contact partner" });

    _mail_get_partner_fields() {
        return ["partner_id"];
    }

    /**
     * @param {integer[]} ids
     * @returns {Object}
     */
    _get_customer_information(ids) {
        const record = this.browse(ids)[0];
        if (!record.email_cc) {
            return;
        }
        const [name, email] = parseEmail(record.email_cc);
        return {
            name,
            email,
            phone: record.phone,
        };
    }

    /** @param {number[]} ids */
    _message_get_suggested_recipients(ids, additional_partners = [], primary_email = false) {
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const result = [];
        const records = this.browse(ids);
        for (const id of ids) {
            const record = records.find((record) => record.id === id);
            if (record.email_cc) {
                MailThread._message_add_suggested_recipient.call(
                    this,
                    id,
                    result,
                    makeKwArgs({
                        name: record.email_cc,
                        email: record.email_cc,
                        partner: undefined,
                        reason: "CC email",
                    })
                );
            }
            if (primary_email) {
                MailThread._message_add_suggested_recipient.call(
                    this,
                    id,
                    result,
                    makeKwArgs({
                        name: primary_email,
                        email: primary_email,
                        partner: undefined,
                        reason: "CC email",
                    })
                );
            }
            const partners = ResPartner.browse(record.partner_ids);
            if (partners.length) {
                for (const partner of partners) {
                    MailThread._message_add_suggested_recipient.call(
                        this,
                        id,
                        result,
                        makeKwArgs({
                            email: partner.email,
                            partner,
                            reason: "Email partner",
                        })
                    );
                }
            }
            const partner_id = additional_partners.length ? additional_partners : record.partner_id;
            const [partner] = ResPartner.browse(partner_id);
            if (partner) {
                MailThread._message_add_suggested_recipient.call(
                    this,
                    id,
                    result,
                    makeKwArgs({
                        email: partner.email,
                        partner,
                        reason: "contact partner",
                    })
                );
            }
        }
        return result;
    }

    /** @param {number[]} ids */
    _message_compute_subject(ids) {
        return new Map(ids.map((id) => [id, "Custom Default Subject"]));
    }
}
