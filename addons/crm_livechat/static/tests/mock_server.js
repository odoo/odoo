/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";


patch(MockServer.prototype, {
    async performRPC(route, args) {
        if (route === "/web/dataset/call_kw/discuss.channel/execute_command_lead") {
            const { body } = args.kwargs;
            const leadName = body.substring("/lead".length).trim();
            const leadId = this.pyEnv["crm.lead"].create({ name: leadName });
            this.pyEnv["bus.bus"]._sendone(
                this.pyEnv.currentPartner,
                "discuss.channel/transient_message", {
                    body: `
                        <span class="o_mail_notification">
                            Create a new lead: <a href="#" data-oe-model="crm.lead" data-oe-id="${leadId}">${leadName}</a>
                        </span>`,
                    model: "discuss.channel",
                    res_id: args.args[0],
                }
            );
            return true;
        }
        return await super.performRPC(...arguments);
    },
});
