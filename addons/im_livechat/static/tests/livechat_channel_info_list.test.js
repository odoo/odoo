import { insertText, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { waitFor } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineLivechatModels();

test("livechat note is loaded when opening the channel info list", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #20",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_note: "<p>Initial note<br/>Second line</p>",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-livechat-ChannelInfoList textarea:value('Initial note\nSecond line')");
});

test("editing livechat note is synced between tabs", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #20",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_note: "<p>Initial note</p>",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: tab1 });
    await openDiscuss(channelId, { target: tab2 });
    await waitFor(".o-livechat-ChannelInfoList textarea:value('Initial note')", { target: tab1 });
    await waitFor(".o-livechat-ChannelInfoList textarea:value('Initial note')", { target: tab2 });
    await insertText(".o-livechat-ChannelInfoList textarea", "Updated note", {
        target: tab1,
        replace: true,
    });
    await document.querySelector(".o-livechat-ChannelInfoList textarea").blur(); // Trigger the blur event to save the note
    await waitFor(".o-livechat-ChannelInfoList textarea:value('Updated note')", { target: tab1 }); // Note should be synced with bus
});
