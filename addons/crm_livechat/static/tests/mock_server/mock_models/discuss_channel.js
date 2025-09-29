import { DiscussChannel } from "@mail/../tests/mock_server/mock_models/discuss_channel";

import { getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    execute_command_lead() {
        const kwargs = getKwArgs(arguments, "ids", "body");
        const ids = kwargs.ids;
        const body = kwargs.body;

        const leadName = body.substring("/lead".length).trim();
        const leadId = this.env["crm.lead"].create({ name: leadName });
        this.message_post(
            ids[0],
            makeKwArgs({
                body: `<div class="o_mail_notification">created a new lead: <a href="#" data-oe-model="crm.lead" data-oe-id="${leadId}">${leadName}</a></div>`,
                subtype_xmlid: "mail.mt_comment",
            })
        );
        return true;
    },
};

patch(DiscussChannel.prototype, discussChannelPatch);
