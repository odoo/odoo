import {
    mailCanAddMessageReactionMobile,
    mailCanCopyTextToClipboardMobile,
} from "@mail/../tests/mail_shared_tests";
import {
    SIZES,
    assertChatHub,
    contains as mailContains,
    defineMailModels,
    openDiscuss,
    openFormView,
    openListView,
    patchUiSize,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { LONG_PRESS_DELAY } from "@mail/utils/common/hooks";
import { describe, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    pointerDown,
    press,
    queryAllRects,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { mockTouch, mockUserAgent } from "@odoo/hoot-mock";

import { location } from "@web/core/browser/browser";
import { contains, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineMailModels();

test("can leave channel in mobile", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor(".o-mail-ChatWindow-moreActions:text('General'):count(1)");
    await contains(".o-mail-ChatWindow-moreActions:text('General'):count(1)").click();
    await waitFor(".o-dropdown-item:text('Leave Conversation'):count(1)");
});

test("enter key should create a newline in composer", async () => {
    mockUserAgent("android");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Test\n");
    await press("Enter");
    await insertTextInComposer(".o-mail-Composer", "Other");
    await contains("[data-icon='send']:count(1)").click();
    await mailContains(".o-mail-Message-body:has(br)", { textContent: "TestOther" });
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
    await waitFor(".o-mail-Message:has(:text('original message')):count(1)");
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await contains("button:text('Edit'):count(1)").click();
    await contains("button:text('Discard editing'):count(1)").click();
    await waitFor(".o-mail-Message:has(:text('original message')):count(1)");
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await contains("button:text('Edit'):count(1)").click();
    await insertTextInComposer(".o-mail-Message .o-mail-Composer", "edited message", {
        replace: true,
    });
    await contains("button[title='Save editing']:count(1)").click();
    await waitFor(".o-mail-Message:has(:text('edited message (edited)')):count(1)");
});

test("Don't show chat hub in discuss app on mobile", async () => {
    mockTouch(true);
    mockUserAgent("android");
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    setupChatHub({ folded: [channelId] });
    await start();
    await waitFor(".o-mail-ChatBubble:count(1)");
    await openDiscuss();
    await waitForNone(".o-mail-ChatBubble");
});

test("click on an odoo link should fold the chat window (mobile)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({});
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", `http://${location.host}/odoo.com`);
    await contains(".o-mail-Composer button[title='Send']:count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains(
        `.o-mail-Message-richBody a[href="http://${location.host}/odoo.com"]:count(1)`
    ).click();
    await waitForNone(".o-mail-ChatWindow");
    await waitForNone(".o-mail-ChatBubble");
    await openListView("discuss.channel", { res_id: channelId });
    await waitFor(".o-mail-ChatBubble:count(1)");
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
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains("a[data-oe-model='res.partner']:count(1)").click();
    await waitFor(".o_form_view:count(1)");
    await waitForNone(".o-mail-ChatWindow");
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
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains("a[data-oe-type='highlight']:count(1)").click();
    await waitFor(".o-mail-Message.o-highlighted .o-mail-Message-content:text(Pin me):count(1)");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("activity mark done popover buttons do not overlap (mobile)", async () => {
    await patchUiSize({ width: 300 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity-markDone.btn:text('Done'):count(1)").click();
    await waitFor(".o-mail-ActivityMarkAsDone button:count(3)");
    await waitFor(
        ".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']:count(1)"
    );
    await waitFor(".o-mail-ActivityMarkAsDone button[aria-label='Done']:count(1)");
    await waitFor(".o-mail-ActivityMarkAsDone button:text('Discard'):count(1)");
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
