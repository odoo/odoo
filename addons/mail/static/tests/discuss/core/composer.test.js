import {
    contains as mailContains,
    defineMailModels,
    focus,
    insertText,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import {
    containsTextInComposer,
    insertTextInComposer,
} from "@mail/../tests/mail_test_helpers_composer";
import { Thread } from "@mail/core/common/thread_model";
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, getService, serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

test('do not send typing notification on typing "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", () => {
        if (!testEnded) {
            expect.step("notify_typing");
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "/");
    await waitFor(".o-mail-Composer button[title='Send']:enabled:count(1)");
    await expect.waitForSteps([]); // No rpc done
    testEnded = true;
});

test('do not send typing notification on typing after selecting suggestion from "/" command', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", () => {
        if (!testEnded) {
            expect.step("notify_typing");
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "/");
    await contains(":nth-child(1 of .o-mail-Composer-suggestion)").click();
    await waitForNone(".o-mail-Composer-suggestion strong");
    await insertTextInComposer(".o-mail-Composer", " is user?");
    await expect.waitForSteps([]); // No rpc done"
    testEnded = true;
});

test("send is_typing on adding emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", () => {
        if (!testEnded) {
            expect.step("notify_typing");
        }
    });
    await start();
    await openDiscuss(channelId);
    await contains("button[title='Add Emojis']:count(1)").click();
    await insertText(".o-EmojiPicker-search input", "Santa Claus");
    await contains(".o-Emoji:text('🎅'):count(1)").click();
    await expect.waitForSteps(["notify_typing"]);
    testEnded = true;
});

test("add an emoji after a command", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await mailContains(".o-mail-Composer-html", { textContent: "" });
    await insertTextInComposer(".o-mail-Composer", "/");
    await contains(":nth-child(2 of .o-mail-Composer-suggestion)").click();
    await containsTextInComposer(".o-mail-Composer", "/who\u00a0");
    await contains("button[title='Add Emojis']:count(1)").click();
    await contains(".o-Emoji:text('😊'):count(1)").click();
    await containsTextInComposer(".o-mail-Composer", "/who\u00a0😊");
});

test.tags("html composer");
test("html composer: send a message in a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await containsTextInComposer(".o-mail-Composer", "");
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await containsTextInComposer(".o-mail-Composer", "Hello");
    await contains(".o-mail-Composer button[title='Send']:enabled:count(1)").click();
    await contains(".o-mail-Message[data-persistent]:contains(Hello):count(1)").click();
    await containsTextInComposer(".o-mail-Composer", "");
});

test.tags("html composer");
test("html composer: trim boundary empty formatting on send", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    let body;
    onRpcBefore("/mail/message/post", (args) => {
        expect.step("/mail/message/post");
        body = args.post_data.body;
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    triggerHotkey("Enter");
    await insertTextInComposer(".o-mail-Composer", "Hello World");
    triggerHotkey("shift+Enter");
    await contains(".o-mail-Composer button[title='Send']:enabled:count(1)").click();
    await expect.waitForSteps(["/mail/message/post"]);
    // Expected editor shape before trimming: '<div><br></div><div">Hello World<br/></div>'
    expect(body).toBe("<div>Hello World</div>");
    await waitFor(".o-mail-Message[data-persistent]:contains(Hello):count(1)");
});

test("keep mentions when channel post is deferred", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { promise, resolve } = Promise.withResolvers();
    patch(Thread.prototype, {
        async post(body, postData = {}, extraData = {}) {
            await promise;
            return super.post(body, postData, extraData);
        },
    });
    onRpcBefore("/mail/message/post", (args) => {
        expect.step("/mail/message/post");
        expect(args.post_data.partner_ids).toEqual([serverState.partnerId]);
        expect(args.post_data.partner_ids_mention_token).toEqual({
            [serverState.partnerId]: serverState.partnerId,
        });
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@");
    await contains(".o-mail-Composer-suggestion strong:text('Mitchell Admin'):count(1)").click();
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00a0");
    await contains(".o-mail-Composer button[title='Send']:enabled:count(1)").click();
    await animationFrame();
    resolve();
    await expect.waitForSteps(["/mail/message/post"]);
    await waitFor(".o-mail-Message-bubble.o-orange:count(1)");
});
