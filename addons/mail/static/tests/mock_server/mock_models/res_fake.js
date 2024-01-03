/** @odoo-module */

import { fields, models } from "@web/../tests/web_test_helpers";

export class ResFake extends models.Model {
    _name = "res.fake";

    activity_ids = fields.One2many({ relation: "mail.activity", string: "Activities" });
    email_cc = fields.Char();
    message_ids = fields.One2many({ relation: "mail.message" });
    message_follower_ids = fields.Char({ string: "Followers" });
    partner_ids = fields.One2many({ relation: "res.partner", string: "Related partners" });

    /**
     * Simulates `_message_get_suggested_recipients` on `res.fake`.
     *
     * @param {string} model
     * @param {number[]} ids
     */
    _messageGetSuggestedRecipients(model, ids) {
        const result = {};
        const records = this.env[model]._filter([["id", "in", ids]]);

        for (const record of records) {
            result[record.id] = [];
            if (record.email_cc) {
                result[record.id].push([false, record.email_cc, undefined, "CC email"]);
            }
            const partners = this.env["res.partner"]._filter([["id", "in", record.partner_ids]]);
            if (partners.length) {
                for (const partner of partners) {
                    result[record.id].push([
                        partner.id,
                        partner.display_name,
                        undefined,
                        "Email partner",
                    ]);
                }
            }
        }
        return result;
    }

    /**
     * Simulates `_message_compute_subject` on `res.fake`.
     *
     * @param {string} model
     * @param {number[]} ids
     */
    _messageComputeSubject(model, ids) {
        if (model === "res.fake") {
            return new Map(ids.map((id) => [id, "Custom Default Subject"]));
        }
        return super.env["mail.thread"]._messageComputeSubject(model, ids);
    }
}
