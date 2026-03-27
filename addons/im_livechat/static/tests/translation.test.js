import { describe, test } from "@odoo/hoot";
import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("message translation in livechat (agent is member)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Mario" }),
                livechat_member_type: "visitor",
            }),
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
    await contains(".o-dropdown-item:contains('Translate')");
});

test("message translation in livechat (agent is not member)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Mario" }),
                livechat_member_type: "visitor",
            }),
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
    await contains(".o-dropdown-item:contains('Translate')");
});
