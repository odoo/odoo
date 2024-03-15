/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/discuss_channel default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    mockCreate(model) {
        if (model !== "mail.canned.response") {
            return super.mockCreate(...arguments);
        }
        const notifications = [];
        const cannedReponseId = super.mockCreate(...arguments);
        const [cannedResponse] = this.getRecords(model, [["id", "=", cannedReponseId]]);
        if (cannedResponse) {
            notifications.push([
                this.pyEnv.currentPartner,
                "mail.record/insert",
                {
                    CannedResponse: [cannedResponse],
                },
            ]);
        }
        if (notifications.length) {
            this.pyEnv["bus.bus"]._sendmany(notifications);
        }
        return cannedReponseId;
    },
    mockWrite(model, args) {
        if (model !== "mail.canned.response") {
            return super.mockWrite(...arguments);
        }
        const res = super.mockWrite(...arguments);
        const [cannedResponse] = this.getRecords(model, [["id", "=", args[0][0]]]);
        this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.record/insert", {
            CannedResponse: [cannedResponse],
        });
        return res;
    },
    mockUnlink(model, args) {
        if (model === "mail.canned.response") {
            this.pyEnv["bus.bus"]._sendone(this.pyEnv.currentPartner, "mail.record/delete", {
                CannedResponse: [
                    {
                        id: args[0][0],
                    },
                ],
            });
        }
        return super.mockUnlink(...arguments);
    },
});
