/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_format_for_chatter` on `mail.followers`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailFollowers_FormatForChatter(ids) {
        const followers = this.getRecords("mail.followers", [["id", "in", ids]]);
        // sorted from lowest ID to highest ID (i.e. from least to most recent)
        followers.sort((f1, f2) => (f1.id < f2.id ? -1 : 1));
        return followers.map((follower) => {
            return {
                id: follower.id,
                partner_id: follower.partner_id,
                name: follower.name,
                display_name: follower.display_name,
                email: follower.email,
                is_active: follower.is_active,
                partner: this._mockResPartnerMailPartnerFormat([follower.partner_id]).get(
                    follower.partner_id
                ),
            };
        });
    },
});
