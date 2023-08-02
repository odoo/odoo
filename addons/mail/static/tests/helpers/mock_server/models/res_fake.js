/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_message_get_suggested_recipients` on `res.fake`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResFake_MessageGetSuggestedRecipients(model, ids) {
        const result = {};
        const records = this.getRecords(model, [["id", "in", ids]]);

        for (const record of records) {
            result[record.id] = [];
            if (record.email_cc) {
                result[record.id].push([false, record.email_cc, undefined, "CC email"]);
            }
            const partners = this.getRecords("res.partner", [["id", "in", record.partner_ids]]);
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
    },
    /**
     * @override
     */
    mockMailThread_MessageComputeSubject(model, ids) {
        if (model === "res.fake") {
            return new Map(ids.map((id) => [id, "Custom Default Subject"]));
        }
        return super.mockMailThread_MessageComputeSubject(model, ids);
    },
});
