import {
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    scroll,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { serverState } from "@web/../tests/web_test_helpers";

import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";

describe.current.tags("desktop");
defineMailModels();

test("Should have a search button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Search Messages']");
});

test("Should open the search panel when search button is clicked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await contains(".o-mail-SearchMessagesPanel");
    await contains(".o_searchview");
    await contains(".o_searchview_input");
});

test("Search a message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

test("Search should be hightlighted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(`.o-mail-SearchMessagesPanel .o-mail-Message .${HIGHLIGHT_CLASS}`);
});

test("Search a starred message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        starred_partner_ids: [serverState.partnerId],
    });
    await start();
    await openDiscuss("mail.box_starred");
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

test("Search a message in inbox", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        needaction: true,
    });
    await start();
    await openDiscuss("mail.box_inbox");
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

test("Search a message in history", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
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
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_history");
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
    await click(".o-mail-SearchMessagesPanel .o-mail-MessageCard-jump");
    await contains(".o-mail-Thread .o-mail-Message.o-highlighted");
});

test("Should close the search panel when search button is clicked again", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await click("[title='Close Search']");
    await contains(".o-mail-SearchMessagesPanel");
});

test("Search a message in 60 messages should return 30 message first", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
    // give enough time to useVisible to potentially load more (unexpected) messages
    await tick();
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
});

test("Scrolling to the bottom should load more searched message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 90; i++) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
    await scroll(".o-mail-SearchMessagesPanel .o-mail-ActionPanel", "bottom");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 60 });
    // give enough time to useVisible to potentially load more (unexpected) messages
    await tick();
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 60 });
});

test("Editing the searched term should not edit the current searched term", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    onRpcBefore("/discuss/channel/messages", (args) => {
        if (args.search_term) {
            const { search_term } = args;
            expect(search_term).toBe("message");
        }
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await insertText(".o_searchview_input", "test");
    await scroll(".o-mail-SearchMessagesPanel .o-mail-ActionPanel", "bottom");
});

test("Search a message containing round brackets", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a (message)",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Search Messages']");
    await insertText(".o_searchview_input", "(message");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

test("Search a message containing single quotes", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "I can't do it");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await click("button[title='Search Messages']");
    await insertText(".o_searchview_input", "can't");
    triggerHotkey("Enter");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});
