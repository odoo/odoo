import { DiscussChannel } from "@mail/../tests/mock_server/mock_models/discuss_channel";

import { getKwArgs, serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    execute_command_lead() {
        const kwargs = getKwArgs(arguments, "ids", "body");
        const ids = kwargs.ids;
        const body = kwargs.body;

        const leadName = body.substring("/lead".length).trim();
        const leadId = this.env["crm.lead"].create({ name: leadName });
        this.env["bus.bus"]._sendone(serverState.partnerId, "discuss.channel/transient_message", {
            body: `
                    <span class="o_mail_notification">
                        Create a new lead: <a href="#" data-oe-model="crm.lead" data-oe-id="${leadId}">${leadName}</a>
                    </span>`,
            thread: { model: "discuss.channel", id: ids[0] },
        });
        return true;
    },
};

patch(DiscussChannel.prototype, discussChannelPatch);
