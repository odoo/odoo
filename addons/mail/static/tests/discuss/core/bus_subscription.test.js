import { waitForChannels } from "@bus/../tests/bus_test_helpers";
import {
    actionPanel,
    click,
    defineMailModels,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, edit, press, test, waitFor, waitForNone } from "@odoo/hoot";

import { Command, contains } from "@web/../tests/web_test_helpers";

defineMailModels();

describe.current.tags("desktop");

test("bus subscription updated when joining/leaving thread as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:text(Hide)");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription updated when opening/closing chat window as a non member", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "Sales",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await waitFor(".o-mail-ChatWindow:has(:text('Sales')):count(1)");
    await waitForChannels([`discuss.channel_${channelId}`]);
    await click("[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow:has(:text('Sales'))"],
    });
    await waitForNone(".o-mail-ChatWindow:has(:text('Sales'))");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
    await press(["control", "k"]);
    await click(".o_command_palette_search input");
    await edit("@");
    await click(".o-mail-DiscussCommand:text('Sales')");
    await waitForChannels([`discuss.channel_${channelId}`]);
});

test("bus subscription updated when joining non-member thread open in discuss", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains("[title='Add People']:count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('Mitchell Admin')):count(1)"
    ).click();
    await contains(".o-discuss-ChannelInvitation button:text('Invite'):enabled:count(1)").click();
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});
