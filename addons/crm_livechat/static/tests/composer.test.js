import { defineCrmLivechatModels } from "@crm_livechat/../tests/crm_livechat_test_helpers";
import {
    click,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineCrmLivechatModels();

test("Can execute lead command", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [
            Command.link(serverState.groupLivechatId),
            Command.link(serverState.groupSalesTeamId),
        ],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    await start();
    onRpc("discuss.channel", "execute_command_lead", ({ args }) => {
        expect.step(args[0]);
        return true;
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/lead great lead");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await expect.waitForSteps([[channelId]]);
});
