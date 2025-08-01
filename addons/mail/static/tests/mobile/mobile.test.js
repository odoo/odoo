import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";

import { asyncStep, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineMailModels();

test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-ChatWindow [title*='Close Chat Window']");
    await contains(".o-mail-MessagingMenu-tab.o-active", { text: "Channels" });
    await click("button", { text: "Mailboxes" });
    await contains(".o-mail-MessagingMenu-tab.o-active", { text: "Mailboxes" });
    await contains("button.active", { text: "Inbox" });
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
    await contains(".o-mail-ChatWindow-command", { text: "General" });
    await click(".o-mail-ChatWindow-command", { text: "General" });
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
