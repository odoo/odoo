import { describe, test } from "@odoo/hoot";
import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("message translation in livechat", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: serverState.publicPartnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Mai mettere l'ananas sulla pizza!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click("[title='Expand']");
    await contains("[title='Translate']");
});
