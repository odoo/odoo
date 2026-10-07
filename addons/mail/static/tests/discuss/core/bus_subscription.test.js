import { waitForChannels } from "@bus/../tests/bus_test_helpers";
import {
    click,
    defineMailModels,
    MENU_ACTIVE_IDS,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import {
    describe,
    edit,
    expect,
    mockDate,
    press,
    runAllTimers,
    test,
    waitFor,
    waitForNone,
} from "@odoo/hoot";

import { Command, contains, getService } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

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
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await contains("[title='Add People']:count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('Mitchell Admin')):count(1)"
    ).click();
    await contains(".o-discuss-ChannelInvitation button:text('Invite'):enabled:count(1)").click();
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales", channel_member_ids: [] },
    ]);
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(later.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"));
    await start();
    await openDiscuss();
    await runAllTimers(); // settle the bus subscriptions from start/openDiscuss
    await triggerHotkey("control+k");
    patch(getService("mail.store"), {
        updateBusSubscription: () => expect.step("update_bus_subscription"),
    });
    await contains(".o-mail-DiscussCommand:has(:text('Sales')):count(1)").click();
    await waitFor(".o-mail-DiscussContent-threadName[title='Sales']:count(1)");
    await contains("button:text('Add People'):count(1)").click();
    await contains("[name='selectablePartnerName']:text('Mitchell Admin'):count(1)").click();
    await contains("button:text('Invite'):count(1)").click();
    await expect.waitForSteps(["update_bus_subscription"]);
});

test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(later.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"));
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-Discuss[data-active]:count(1)");
    await runAllTimers(); // settle the bus subscriptions from start/openDiscuss
    await openDiscuss();
    patch(getService("mail.store"), {
        updateBusSubscription: () => expect.step("update_bus_subscription"),
    });
    await waitFor(".o-mail-MessagingMenuItem:count(1)");
    await waitFor(".o-mail-MessagingMenuItem:has(:text('General')):count(1)");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Conversation')");
    await click(".o_dialog button:text('Leave Conversation')");
    await waitForNone(".o-mail-MessagingMenuItem");
    await expect.waitForSteps(["update_bus_subscription"]);
});
