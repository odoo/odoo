/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/res_fake default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { parseEmail } from "@mail/utils/common/format";

patch(MockServer.prototype, {
    /**
     * Simulates `_get_customer_information` on `res.fake`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailThread_GetCustomerInformation(model, ids) {
        if (model !== "res.fake") {
            return this._super(model, ids);
        }
        const record = this.getRecords(model, [["id", "in", ids]])[0];
        const [name, email] = parseEmail(record.email_cc);
        return {
            name,
            email,
            phone: record.phone,
        };
    },
    /**
     * Simulates `_message_get_suggested_recipients` on `res.fake`.
     *
     * @private
     * @param {string} model
     * @param {integer} id
     * @returns {Object}
     */
    _mockResFake_MessageGetSuggestedRecipients(model, id) {
        const result = [];
        const record = this.getRecords(model, [["id", "=", id]])[0];

        if (record.email_cc) {
            this._mockMailThread_MessageAddSuggestedRecipient(model, id, result, {
                name: record.email_cc,
                email: record.email_cc,
                partner: undefined,
                reason: "CC email",
            });
        }
        const partners = this.getRecords("res.partner", [["id", "in", record.partner_ids]]);
        if (partners.length) {
            for (const partner of partners) {
                this._mockMailThread_MessageAddSuggestedRecipient(model, id, result, {
                    email: partner.email,
                    partner,
                    reason: "Email partner",
                });
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
