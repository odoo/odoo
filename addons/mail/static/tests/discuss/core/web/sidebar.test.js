import { waitForChannels, waitNotifications } from "@bus/../tests/bus_test_helpers";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { Command } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("unknown channel can be displayed and interacted with", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: partnerId })],
        channel_type: "channel",
        name: "Not So Secret",
    });
    const env = await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Not So Secret" });
    await insertText(".o-mail-Composer-input", "Hello", { replace: true });
    await press("Enter");
    await contains(".o-mail-Message", { text: "Hello" });
    await waitNotifications([env, "discuss.channel/new_message"]);
    await click("button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "Not So Secret" });
    await click("[title='Leave Channel']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Not So Secret" }],
    });
    await click("button", { text: "Leave Conversation" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});
