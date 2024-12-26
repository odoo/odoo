import { waitNotifications } from "@bus/../tests/bus_test_helpers";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { RATING } from "@im_livechat/embed/common/livechat_service";
import {
    click,
    contains,
    insertText,
    onRpcBefore,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    asyncStep,
    Command,
    mountWithCleanup,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Do not ask feedback if empty", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await click("[title*='Close Chat Window']");
});

test("Close without feedback", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore((route) => {
        if (route === "/im_livechat/visitor_leave_session" || route === "/im_livechat/feedback") {
            asyncStep(route);
        }
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await click("button", { text: "Close" });
    await contains(".o-livechat-LivechatButton");
    await waitForSteps(["/im_livechat/visitor_leave_session"]);
});

test("Feedback with rating and comment", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore((route, args) => {
        if (route === "/im_livechat/visitor_leave_session") {
            asyncStep(route);
        }
        if (route === "/im_livechat/feedback") {
            asyncStep(route);
            expect(args.reason.includes("Good job!")).toBe(true);
            expect(args.rate).toBe(RATING.GOOD);
        }
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await waitForSteps(["/im_livechat/visitor_leave_session"]);
    await click(`img[data-alt="${RATING.GOOD}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:contains(Send):enabled");
    await contains("p", { text: "Thank you for your feedback" });
    await waitForSteps(["/im_livechat/feedback"]);
});

test("Closing folded chat window should open it with feedback", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title='Fold']");
    await waitNotifications([env, "discuss.Thread/fold_state"]);
    await click(".o-mail-ChatBubble");
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await click(".o-mail-ChatHub-bubbleBtn");
    await contains(".o-mail-ChatWindow p", { text: "Did we correctly answer your question?" });
});

test("Start new session from feedback panel", async () => {
    const pyEnv = await startServer();
    const channelId = await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin" });
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    pyEnv["im_livechat.channel"].write([channelId], {
        user_ids: [
            Command.clear(serverState.userId),
            Command.create({ partner_id: pyEnv["res.partner"].create({ name: "Bob Operator" }) }),
        ],
    });
    await click("button", { text: "New Session" });
    await contains(".o-mail-ChatWindow", { count: 1 });
    await contains(".o-mail-ChatWindow", { text: "Bob Operator" });
});
