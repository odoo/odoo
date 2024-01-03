/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class MailFollowers extends models.ServerModel {
    _name = "mail.followers";

    /**
     * Simulates `_format_for_chatter` on `mail.followers`.
     *
     * @returns {number[]} ids
     */
    _formatForChatter(ids) {
        // sorted from lowest ID to highest ID (i.e. from least to most recent)
        return this.env["mail.followers"]
            ._filter([["id", "in", ids]])
            .sort((f1, f2) => (f1.id < f2.id ? -1 : 1))
            .map((follower) => {
                return {
                    id: follower.id,
                    partner_id: follower.partner_id,
                    name: follower.name,
                    display_name: follower.display_name,
                    email: follower.email,
                    is_active: follower.is_active,
                    partner: this.env["res.partner"].mail_partner_format([follower.partner_id])[
                        follower.partner_id
                    ],
                };
            });
    }
}
