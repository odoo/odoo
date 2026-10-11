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
import { describe, test } from "@odoo/hoot";
import { advanceTime, pointerDown, press, waitFor, waitForNone } from "@odoo/hoot-dom";
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
    await waitFor(".o-mail-ChatWindow-moreActions:text('General'):count(1)");
    await click(".o-mail-ChatWindow-moreActions:text('General')");
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
    await waitFor(".o-mail-Message:has(:text('original message')):count(1)");
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await click("button:text('Edit')");
    await click("button:text('Discard editing')");
    await waitFor(".o-mail-Message:has(:text('original message')):count(1)");
    await pointerDown(".o-mail-Message", { contains: "original message" });
    await advanceTime(LONG_PRESS_DELAY);
    await click("button:text('Edit')");
    await insertTextInComposer(".o-mail-Message .o-mail-Composer", "edited message", {
        replace: true,
    });
    await click("button[title='Save editing']");
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
    await click(".o-mail-Composer button[title='Send']");
    await waitFor(".o-mail-ChatWindow:count(1)");
    await click(`.o-mail-Message-richBody a[href="http://${location.host}/odoo.com"]`);
    await waitForNone(".o-mail-ChatWindow");
    await waitForNone(".o-mail-ChatBubble");
    await openListView("discuss.channel", { res_id: channelId });
    await waitFor(".o-mail-ChatBubble:count(1)");
    assertChatHub({ folded: [channelId] });
});
