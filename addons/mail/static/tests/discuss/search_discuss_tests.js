/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText, scroll } from "@web/../tests/utils";

QUnit.module("discuss search");

QUnit.test("Should have a search button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains("[title='Search Messages']");
});

QUnit.test("Should open the search panel when search button is clicked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await contains(".o-mail-SearchMessagesPanel");
    await contains(".o_searchview");
    await contains(".o_searchview_input");
});

QUnit.test("Search a message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

QUnit.test("Search should be hightlighted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessagesPanel .o-mail-Message .${HIGHLIGHT_CLASS}`);
});

QUnit.test("Search a starred message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        starred_partner_ids: [pyEnv.currentPartnerId],
    });
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_starred");
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

QUnit.test("Search a message in inbox", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_inbox");
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

QUnit.test("Search a message in history", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        needaction: false,
    });
    pyEnv["mail.notification"].create({
        is_read: true,
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_history");
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

QUnit.test("Should close the search panel when search button is clicked again", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await click("[title='Close Search']");
    await contains(".o-mail-SearchMessagesPanel");
});

QUnit.test("Search a message in 60 messages should return 30 message first", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
});

QUnit.test("Scrolling to the bottom should load more searched message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
    await scroll(".o-mail-SearchMessagesPanel .o-mail-ActionPanel", "bottom");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 60 });
});

QUnit.test(
    "Editing the searched term should not edit the current searched term",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        for (let i = 0; i < 60; i++) {
            pyEnv["mail.message"].create({
                author_id: pyEnv.currentPartnerId,
                body: "This is a message",
                attachment_ids: [],
                message_type: "comment",
                model: "discuss.channel",
                res_id: channelId,
            });
        }
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/messages" && args.search_term) {
                    const { search_term } = args;
                    assert.strictEqual(search_term, "message");
                }
            },
        });
        await openDiscuss(channelId);
        await click("[title='Search Messages']");
        await insertText(".o_searchview_input", "message");
        triggerHotkey("Enter");
        await insertText(".o_searchview_input", "test");
        await scroll(".o-mail-SearchMessagesPanel .o-mail-ActionPanel", "bottom");
    }
);
