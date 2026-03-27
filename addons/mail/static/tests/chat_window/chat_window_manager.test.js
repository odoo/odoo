import {
    click,
    contains,
    defineMailModels,
    onRpcBefore,
    patchUiSize,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { CHAT_HUB_KEY } from "@mail/core/common/chat_hub_model";
import { describe, expect, test } from "@odoo/hoot";
import { asyncStep, getService, waitForSteps } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

describe.current.tags("desktop");
defineMailModels();

test("chat window does not fetch messages if hidden", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([{}, {}, {}]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Banana",
            res_id: channelId3,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    patchUiSize({ width: 900 }); // enough for 2 open chat windows max
    onRpcBefore("/discuss/channel/messages", () => asyncStep("fetch_messages"));
    setupChatHub({ opened: [channelId3, channelId2, channeId1] });
    await start();
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatBubble", { count: 1 });
    // FIXME: expected ordering: Banana, Apple, Orange
    await contains(".o-mail-Message-content", { text: "Banana" });
    await contains(".o-mail-Message-content", { text: "Apple" });
    await contains(".o-mail-Message-content", { count: 0, text: "Orange" });
    await waitForSteps(["fetch_messages", "fetch_messages"]);
});

test("click on hidden chat window should fetch its messages", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([{}, {}, {}]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Banana",
            res_id: channelId3,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    patchUiSize({ width: 900 }); // enough for 2 open chat windows max
    onRpcBefore("/discuss/channel/messages", () => asyncStep("fetch_messages"));
    setupChatHub({ opened: [channelId3, channelId2, channeId1] });
    await start();
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatBubble", { count: 1 });
    // FIXME: expected ordering: Banana, Apple, Orange
    await contains(".o-mail-Message-content", { text: "Banana" });
    await contains(".o-mail-Message-content", { text: "Apple" });
    await contains(".o-mail-Message-content", { count: 0, text: "Orange" });
    await waitForSteps(["fetch_messages", "fetch_messages"]);
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-Message-content", { text: "Orange" });
    await contains(".o-mail-Message-content", { text: "Banana" });
    await contains(".o-mail-Message", { count: 0, text: "Apple" });
    await waitForSteps(["fetch_messages"]);
});

test("downgrade 19.1 to 19.0 should ignore chat hub local storage data", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    // simulate data in local storage like 19.1
    browser.localStorage.setItem(
        CHAT_HUB_KEY,
        JSON.stringify({
            opened: [{ id: channelId }],
            folded: [{ id: 1000 }],
        })
    );
    await start();
    const store = getService("mail.store");
    await store.chatHub.initPromise;
    expect(browser.localStorage.getItem(CHAT_HUB_KEY)).toBe(null);
    await contains(".o-mail-ChatHub");
    await contains(".o-mail-ChatHub .o-mail-ChatWindow", { count: 0 });
    await contains(".o-mail-ChatHub .o-mail-ChatBubble", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    expect(browser.localStorage.getItem(CHAT_HUB_KEY)).toBe(
        JSON.stringify({ opened: [{ id: channelId, model: "discuss.channel" }], folded: [] })
    );
    await click(".o-mail-ChatWindow-header [title='Fold']");
    await contains(".o-mail-ChatBubble");
    expect(browser.localStorage.getItem(CHAT_HUB_KEY)).toBe(
        JSON.stringify({ opened: [], folded: [{ id: channelId, model: "discuss.channel" }] })
    );
});
