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
    openDiscuss,
    openFormView,
    openListView,
    patchUiSize,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { LONG_PRESS_DELAY } from "@mail/utils/common/hooks";
import { describe, test } from "@odoo/hoot";
import { advanceTime, pointerDown, press } from "@odoo/hoot-dom";
import { mockTouch, mockUserAgent } from "@odoo/hoot-mock";

import { location } from "@web/core/browser/browser";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineMailModels();

test("can leave channel in mobile", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains(".o-mail-ChatWindow-moreActions:text('General')");
    await click(".o-mail-ChatWindow-moreActions:text('General')");
    await contains(".o-dropdown-item:text('Leave Conversation')");
});

test("enter key should create a newline in composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test\n");
    await press("Enter");
    await insertText(".o-mail-Composer-input", "Other");
    await click("[data-icon='send']");
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
    await contains(".o-mail-Message:has(:text('original message'))");
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await click("button:text('Edit')");
    await click("button:text('Discard editing')");
    await contains(".o-mail-Message:has(:text('original message'))");
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await click("button:text('Edit')");
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click("button[title='Save editing']");
    await contains(".o-mail-Message:has(:text('edited message (edited)'))");
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
    await insertText(".o-mail-Composer-input", `http://${location.host}/odoo.com`);
    await click(".o-mail-Composer button[title='Send']");
    await contains(".o-mail-ChatWindow");
    await click(`.o-mail-Message-richBody a[href="http://${location.host}/odoo.com"]`);
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
