import {
    mailCanAddMessageReactionMobile,
    mailCanCopyTextToClipboardMobile,
} from "@mail/../tests/mail_shared_tests";
import {
    SIZES,
    assertChatHub,
    click,
    contains,
    defineMailModels,
    insertText,
    listenStoreFetch,
    openDiscuss,
    openFormView,
    openListView,
    patchUiSize,
    setupChatHub,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { LONG_PRESS_DELAY } from "@mail/utils/common/hooks";
import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, pointerDown, press, queryAllRects } from "@odoo/hoot-dom";
import { Deferred, mockTouch, mockUserAgent } from "@odoo/hoot-mock";

import { browser } from "@web/core/browser/browser";
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

test("can add message reaction (mobile)", mailCanAddMessageReactionMobile);

test("can copy text to clipboard (mobile)", mailCanCopyTextToClipboardMobile);

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

test("Don't show chat hub in discuss app on mobile", async () => {
    mockTouch(true);
    mockUserAgent("android");
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    setupChatHub({ folded: [channelId] });
    await start();
    await contains(".o-mail-ChatBubble");
    await openDiscuss();
    await contains(".o-mail-ChatBubble", { count: 0 });
});

test("click on an odoo link should fold the chat window (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", `http://${browser.location.host}/odoo.com`);
    await click(".o-mail-Composer button[title='Send']");
    await contains(".o-mail-ChatWindow");
    await click(`a[href="http://${browser.location.host}/odoo.com"]`);
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-mail-ChatBubble", { count: 0 });
    await openListView("discuss.channel", { res_id: channelId });
    await contains(".o-mail-ChatBubble");
    assertChatHub({ folded: [channelId] });
});

test("click on a record link should fold the chat window (mobile)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Lead customer" });
    const channelId = pyEnv["discuss.channel"].create({});
    pyEnv["mail.message"].create({
        body: `<a href="#" data-oe-model="res.partner" data-oe-id="${partnerId}">Lead customer</a>`,
        model: "discuss.channel",
        res_id: channelId,
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ChatWindow");
    await click("a[data-oe-model='res.partner']");
    await contains(".o_form_view");
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test("click on a pin notification link highlights the message without folding the chat window (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "Pin me",
        model: "discuss.channel",
        res_id: channelId,
    });
    await pyEnv["discuss.channel"].set_message_pin(channelId, messageId, true);
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ChatWindow");
    await click("a[data-oe-type='highlight']");
    await contains(".o-mail-Message.o-highlighted .o-mail-Message-content:text(Pin me):count(1)");
    await contains(".o-mail-ChatWindow");
});

test("activity mark done popover buttons do not overlap (mobile)", async () => {
    await patchUiSize({ width: 360 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".btn:text('Mark Done')");
    await contains(".o-mail-ActivityMarkAsDone button", { count: 3 });
    const rects = queryAllRects(".o-mail-ActivityMarkAsDone button");
    for (let i = 1; i < rects.length; i++) {
        if (Math.round(rects[i].top) === Math.round(rects[i - 1].top)) {
            expect(rects[i].left).toBeGreaterThan(rects[i - 1].right);
        } else {
            expect(rects[i].left).toBe(rects[0].left);
            expect(rects[i].top).toBeGreaterThan(rects[i - 1].bottom);
        }
    }
});
