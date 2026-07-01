import {
    click,
    contains,
    defineMailModels,
    editInput,
    insertText,
    openDiscuss,
    patchUiSize,
    scroll,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { expect, mockUserAgent, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import { serverState } from "@web/../tests/web_test_helpers";

import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";

defineMailModels();

test.tags("desktop");
test("Should have a search button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Search Messages']");
});

test.tags("desktop");
test("Should open the search panel when search button is clicked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("[title='Search Messages']");
    await contains(".o-mail-SearchMessagesPanel");
    await contains(".o-mail-SearchMessageInput");
    await contains(".o-mail-SearchInput input");
});

test.tags("desktop");
test("Should open the search panel with hotkey 'f'", async () => {
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
    await contains(".o-mail-Message");
    await press("alt+f");
    await contains(".o-mail-SearchMessagesPanel");
});

test.tags("desktop");
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
    await contains(".o-mail-Message");
    await click("button[title='Search Messages']");
    await contains(".o-mail-SearchMessageInput .o-mail-SearchInput input");
    await editInput(document.body, ".o-mail-SearchInput input", "message");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
    expect(".o-mail-SearchInput input").toHaveValue("message");
    await click("button[aria-label='Clear']");
    await contains(".o-mail-SearchMessagesPanel:not(:has(.o-mail-Message))");
    expect(".o-mail-SearchInput input").toHaveValue("");
});

test.tags("desktop");
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
    await contains(".o-mail-Message");
    await click("[title='Search Messages']");
    await contains(".o-mail-SearchMessageInput");
    await insertText(".o-mail-SearchInput input", "message");
    await contains(`.o-mail-SearchMessagesPanel .o-mail-Message .${HIGHLIGHT_CLASS}`);
});

test.tags("desktop");
test("Should close the search panel when search button is clicked again", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("[title='Search Messages']");
    await click("[title='Close Search']");
    await contains(".o-mail-SearchMessagesPanel");
});

test.tags("desktop");
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
    await contains(".o-mail-Message", { count: 30 });
    await click("[title='Search Messages']");
    await contains(".o-mail-SearchMessageInput");
    await insertText(".o-mail-SearchInput input", "message");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
    // give enough time to useVisible to potentially load more (unexpected) messages
    await tick();
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
});

test.tags("desktop");
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
    await contains(".o-mail-Message", { count: 30 });
    await click("[title='Search Messages']");
    await contains(".o-mail-SearchMessageInput");
    await insertText(".o-mail-SearchInput input", "message");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 30 });
    await scroll(".o-mail-SearchMessagesPanel .o-mail-ActionPanel", "bottom");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 60 });
    // give enough time to useVisible to potentially load more (unexpected) messages
    await tick();
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message", { count: 60 });
});

test.tags("desktop");
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
    await contains(".o-mail-Message");
    await click("button[title='Search Messages']");
    await contains(".o-mail-SearchMessageInput");
    await insertText(".o-mail-SearchInput input", "(message");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

test.tags("desktop");
test("Search a message containing single quotes", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "I can't do it");
    await click(".o-sendMessageActive:enabled");
    await contains(".o-mail-Message");
    await click("button[title='Search Messages']");
    await contains(".o-mail-SearchMessageInput");
    await insertText(".o-mail-SearchInput input", "can't");
    await contains(".o-mail-SearchMessagesPanel .o-mail-Message");
});

test.tags("mobile");
test("Close message search panel when navigating back on mobile", async () => {
    mockUserAgent("android");
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-ChatWindow-moreActions");
    await click("button:text('Search Messages')");
    await contains(".o-mail-SearchMessagesPanel");
    history.back();
    await contains(".o-mail-SearchMessagesPanel", { count: 0 });
});
