import { waitNotifications } from "@bus/../tests/bus_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { RATING } from "@im_livechat/embed/common/livechat_service";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    insertText,
    onRpcBefore,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Do not ask feedback if empty", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await click("[title='Close Chat Window']");
});

test("Close without feedback", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore((route) => {
        if (route === "/im_livechat/visitor_leave_session") {
            step(route);
        }
        if (route === "/im_livechat/feedback") {
            step(route);
        }
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click("[title='Close Chat Window']");
    await click("button", { text: "Close conversation" });
    await contains(".o-livechat-LivechatButton");
    await assertSteps(["/im_livechat/visitor_leave_session"]);
});

test("Feedback with rating and comment", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore((route, args) => {
        if (route === "/im_livechat/visitor_leave_session") {
            step(route);
        }
        if (route === "/im_livechat/feedback") {
            step(route);
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
    await click("[title='Close Chat Window']");
    await assertSteps(["/im_livechat/visitor_leave_session"]);
    await click(`img[data-alt="${RATING.GOOD}"]`);
    await insertText("textarea[placeholder='Explain your note']", "Good job!");
    await click("button:enabled", { text: "Send" });
    await contains("p", { text: "Thank you for your feedback" });
    await assertSteps(["/im_livechat/feedback"]);
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
    await contains(".o-mail-ChatWindow.o-folded");
    await click("[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow.o-folded", { count: 0 });
    await contains(".o-mail-ChatWindow p", { text: "Did we correctly answer your question?" });
});
