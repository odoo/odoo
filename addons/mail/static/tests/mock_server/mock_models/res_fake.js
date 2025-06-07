import { parseEmail } from "@mail/utils/common/format";
import { fields, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class ResFake extends models.Model {
    _name = "res.fake";

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    };

    name = fields.Char({ string: "Name" });
    activity_ids = fields.One2many({ relation: "mail.activity", string: "Activities" });
    email_cc = fields.Char();
    message_ids = fields.One2many({ relation: "mail.message" });
    message_follower_ids = fields.Many2many({ relation: "mail.followers", string: "Followers" });
    partner_ids = fields.One2many({ relation: "res.partner", string: "Related partners" });
    phone = fields.Char({ string: "Phone number" });

    /**
     * @param {integer[]} ids
     * @returns {Object}
     */
    _get_customer_information(ids) {
        const record = this.browse(ids)[0];
        const [name, email] = parseEmail(record.email_cc);
        return {
            name,
            email,
            phone: record.phone,
        };
    }

    /** @param {number[]} ids */
    _message_get_suggested_recipients(ids) {
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
        }
        return result;
    }

    /** @param {number[]} ids */
    _message_compute_subject(ids) {
        return new Map(ids.map((id) => [id, "Custom Default Subject"]));
    }
}
