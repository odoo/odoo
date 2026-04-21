import { insertText as htmlInsertText } from "@html_editor/../tests/_helpers/user_actions";

import {
    click,
    contains,
    defineMailModels,
    focus,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { Composer } from "@mail/core/common/composer";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    // Simulate real user interactions
    patchWithCleanup(Composer.prototype, {
        isEventTrusted() {
            return true;
        },
    });
});

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
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-Composer button[title='Send']:enabled");
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
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(1 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " is user?");
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
    await click("button[title='Add Emojis']");
    await insertText("input[placeholder='Search emoji']", "Santa Claus");
    await click(".o-Emoji:text('🎅')");
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
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "/");
    await click(":nth-child(3 of .o-mail-Composer-suggestion)");
    await contains(".o-mail-Composer-input", { value: "/who " });
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('😊')");
    await contains(".o-mail-Composer-input", { value: "/who 😊" });
});

test.tags("html composer");
test("html composer: send a message in a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "Hello");
    await contains(".o-mail-Composer-html.odoo-editor-editable:text('Hello')");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await click(".o-mail-Message[data-persistent]:contains(Hello)");
    await contains(".o-mail-Composer-html.odoo-editor-editable", { textContent: "" });
});

test("Show self-avatar in composer of Discuss App", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-avatar");
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    await contains(
        `img.o-mail-Composer-avatar[data-src='${getOrigin()}/web/image/res.partner/${
            serverState.partnerId
        }/avatar_128?unique=${deserializeDateTime(partner.write_date).ts}']`
    );
    // but not in chat window
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Chatter");
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow .o-mail-Composer");
    await contains(".o-mail-ChatWindow .o-mail-Composer-avatar", { count: 0 });
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
    await openDiscuss(channelId);
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    triggerHotkey("Enter");
    await htmlInsertText(editor, "Hello World");
    triggerHotkey("shift+Enter");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await expect.waitForSteps(["/mail/message/post"]);
    // Expected editor shape before trimming: '<div><br></div><div">Hello World<br/></div>'
    expect(body).toBe('<div>Hello World</div>');
    await contains(".o-mail-Message[data-persistent]:contains(Hello)");
});
