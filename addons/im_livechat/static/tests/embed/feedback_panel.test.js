import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
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
import { expect, test } from "@odoo/hoot";
import {
    asyncStep,
    Command,
    getService,
    patchWithCleanup,
    serverState,
    waitForSteps,
    withUser,
} from "@web/../tests/web_test_helpers";

defineLivechatModels();

test("Do not ask feedback if empty", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
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
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await click("button", { text: "Close" });
    await contains(".o-livechat-LivechatButton");
    await waitForSteps(["/im_livechat/visitor_leave_session"]);
});

test("Last operator leaving ends the livechat", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    const operatorUserId = serverState.userId;
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    // simulate operator leaving
    await withUser(operatorUserId, () =>
        getService("orm").call("discuss.channel", "action_unfollow", [
            [Object.values(getService("mail.store").Thread.records).at(-1).id],
        ])
    );
    await contains("span", { text: "This livechat conversation has ended" });
    await contains(".o-mail-Composer-input", { count: 0 });
    await click("[title*='Close Chat Window']");
    await contains("p", { text: "Did we correctly answer your question?" }); // shows immediately feedback
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
            expect(args.reason).toInclude("Good job!");
            expect(args.rate).toBe(RATING.OK);
        }
    });
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await waitForSteps(["/im_livechat/visitor_leave_session"]);
    await click(`img[alt="${RATING.OK}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:contains(Send):enabled");
    await contains("p", { text: "Thank you for your feedback" });
    await waitForSteps(["/im_livechat/feedback"]);
});

test("Closing folded chat window should open it with feedback", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await click("[title='Fold']");
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
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin" });
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    pyEnv["im_livechat.channel"].write([channelId], {
        user_ids: [Command.clear(serverState.userId)],
    });
    pyEnv["im_livechat.channel"].write([channelId], {
        user_ids: [
            pyEnv["res.users"].create({
                partner_id: pyEnv["res.partner"].create({ name: "Bob Operator" }),
            }),
        ],
    });

    await click("button", { text: "New Session" });
    await contains(".o-mail-ChatWindow", { count: 1 });
    await contains(".o-mail-ChatWindow", { text: "Bob Operator" });
});

test("open review link on good rating", async () => {
    patchWithCleanup(window, {
        open: (...args) => {
            expect.step("window.open");
            expect(args[0]).toBe("https://www.odoo.com");
            expect(args[1]).toBe("_blank");
        },
    });
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await click(`img[alt="${RATING.GOOD}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:contains(Send):enabled");
    await expect.waitForSteps(["window.open"]);
});
