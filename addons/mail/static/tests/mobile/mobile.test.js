import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    patchUiSize,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { LONG_PRESS_DELAY } from "@mail/utils/common/hooks";
import { describe, test } from "@odoo/hoot";
import { advanceTime, pointerDown, press } from "@odoo/hoot-dom";
import { Deferred, mockTouch, mockUserAgent } from "@odoo/hoot-mock";

import { asyncStep, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineMailModels();

test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-ChatWindow [title*='Close Chat Window']");
    await contains(".o-mail-MessagingMenu-tab.active", { text: "Channels" });
    await click("button", { text: "Inbox" });
    await contains(".o-mail-MessagingMenu-tab.active", { text: "Inbox" });
    await contains(".btn-secondary.active", { text: "Inbox" }); // in header
});

test("show loading on initial opening", async () => {
    // This could load a lot of data (all pinned conversations)
    const def = new Deferred();
    listenStoreFetch("channels_as_member", {
        async onRpc() {
            asyncStep("before channels_as_member");
            await def;
        },
    });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu .fa.fa-circle-o-notch.fa-spin");
    await contains(".o-mail-NotificationItem", { text: "General", count: 0 });
    await waitForSteps(["before channels_as_member"]);
    def.resolve();
    await waitStoreFetch("channels_as_member");
    await contains(".o-mail-MessagingMenu .fa.fa-circle-o-notch.fa-spin", { count: 0 });
    await contains(".o-mail-NotificationItem", { text: "General" });
});

test("can leave channel in mobile", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains(".o-mail-ChatWindow-moreActions", { text: "General" });
    await click(".o-mail-ChatWindow-moreActions", { text: "General" });
    await contains(".o-dropdown-item", { text: "Leave Channel" });
});

test("enter key should create a newline in composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test\n");
    await press("Enter");
    await insertText(".o-mail-Composer-input", "Other");
    await click(".fa-paper-plane-o");
    await contains(".o-mail-Message-body:has(br)", { textContent: "TestOther" });
});

// FIXME: test doesn't work on runbot, somehow it runs there as if isMobileOS() is false
test.skip("can add message reaction (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Hello world" });
    await click(".o-mail-Message [title='Expand']");
    await click(".modal button:contains('Add a Reaction')");
    await click(".modal .o-EmojiPicker .o-Emoji:contains('😀')");
    await contains(".o-mail-MessageReaction:contains('😀')");
    // Can quickly add new reactions
    await click(".o-mail-MessageReactions button[title='Add Reaction']");
    await click(".modal .o-EmojiPicker .o-Emoji:contains('🤣')");
    await contains(".o-mail-MessageReaction:contains('🤣')");
    await contains(".o-mail-MessageReaction:contains('😀')");
});

test("Can edit message comment in chatter (mobile)", async () => {
    mockTouch(true);
    mockUserAgent("android");
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "original message",
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { text: "original message" });
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await click("button", { text: "Edit" });
    await click("button", { text: "Discard editing" });
    await contains(".o-mail-Message", { text: "original message" });
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await click("button", { text: "Edit" });
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click("button[title='Save editing']");
    await contains(".o-mail-Message", { text: "edited message (edited)" });
});
