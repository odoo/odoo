import { defineCrmLivechatModels } from "@crm_livechat/../tests/crm_livechat_test_helpers";
import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineCrmLivechatModels();

test("open leads of the visitor are shown in the channel info list", async () => {
    const pyEnv = await startServer();
    const customerPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    pyEnv["crm.lead"].create({ name: "Bob wants a demo", partner_id: customerPartnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ livechat_member_type: "agent", partner_id: serverState.partnerId }),
            Command.create({ livechat_member_type: "visitor", partner_id: customerPartnerId }),
        ],
        channel_type: "livechat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-livechat-ChannelInfoList h6:text('Open leads')");
    await contains(
        ".o-livechat-ChannelInfoList a[data-oe-model='crm.lead']:text('Bob wants a demo')"
    );
});
