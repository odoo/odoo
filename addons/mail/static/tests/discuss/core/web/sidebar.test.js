import { waitForChannels } from "@bus/../tests/bus_test_helpers";
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
import { asyncStep, Command, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("sidebar find shows channels matching search term", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        channel_type: "channel",
        group_public_id: false,
        name: "test",
    });
    await start();
    await openDiscuss();
    await click(
        ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-add"
    );
    await insertText(".o-discuss-ChannelSelector input", "test");
    // When searching for a single existing channel, the results list will have at least 2 lines:
    // One for the existing channel itself
    // One for creating a channel with the search term
    await contains(".o-mail-NavigableList-item", { count: 2 });
    await contains(".o-mail-NavigableList-item", { text: "test" });
    await contains(".o-mail-NavigableList-item", { text: "Create: # test" });
});

test("sidebar find shows channels matching search term even when user is member", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "channel",
        group_public_id: false,
        name: "test",
    });
    await start();
    await openDiscuss();
    await click(
        ":nth-child(1 of .o-mail-DiscussSidebarCategory) .o-mail-DiscussSidebarCategory-add"
    );
    await insertText(".o-discuss-ChannelSelector input", "test");
    // When searching for a single existing channel, the results list will have at least 2 lines:
    // One for the existing channel itself
    // One for creating a channel with the search term
    await contains(".o-mail-NavigableList-item", { count: 2 });
    await contains(".o-mail-NavigableList-item", { text: "test" });
    await contains(".o-mail-NavigableList-item", { text: "Create: # test" });
});

test("unknown channel can be displayed and interacted with", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: partnerId })],
        channel_type: "channel",
        name: "Not So Secret",
    });
    const env = await start();
    env.services.bus_service.subscribe("discuss.channel/new_message", () =>
        asyncStep("discuss.channel/new_message")
    );
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Not So Secret" });
    await insertText(".o-mail-Composer-input", "Hello", { replace: true });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: "Hello" });
    await waitForSteps(["discuss.channel/new_message"]);
    await click("button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "Not So Secret" });
    await click("[title='Leave Channel']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Not So Secret" }],
    });
    await click("button", { text: "Leave Conversation" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});
