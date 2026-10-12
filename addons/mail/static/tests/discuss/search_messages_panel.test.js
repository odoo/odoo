import {
    click,
    contains,
    defineMailModels,
    editInput,
    insertText,
    listenStoreFetch,
    openDiscuss,
    patchUiSize,
    scroll,
    SIZES,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { animationFrame, expect, mockUserAgent, test } from "@odoo/hoot";
import { press, waitFor, waitForNone } from "@odoo/hoot-dom";
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
    await waitFor("[title='Search Messages']:count(1)");
});

test.tags("desktop");
test("Should open the search panel when search button is clicked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("[title='Search Messages']");
    await waitFor(".o-mail-SearchMessagesPanel:count(1)");
    await waitFor(".o-mail-ActionPanel-header .o-mail-SearchMessageInput:count(1)");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput input:count(1)");
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
    await waitFor(".o-mail-Message:count(1)");
    await press("alt+f");
    await waitFor(".o-mail-SearchMessagesPanel:count(1)");
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
    await waitFor(".o-mail-Message:count(1)");
    await click("button[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput input:count(1)");
    await editInput(
        document.body,
        ".o-mail-SearchMessageInput .o-mail-SearchInput input",
        "message"
    );
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(1)");
    expect(".o-mail-SearchMessageInput .o-mail-SearchInput input").toHaveValue("message");
    await click("button[aria-label='Clear']");
    await waitFor(".o-mail-SearchMessagesPanel:not(:has(.o-mail-Message)):count(1)");
    expect(".o-mail-SearchMessageInput .o-mail-SearchInput input").toHaveValue("");
});

test.tags("desktop");
test("Searching messages shows spinner icon", async () => {
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
    let blockedFetchMessages = Promise.withResolvers();
    listenStoreFetch("/discuss/channel/messages", {
        logParams: ["/discuss/channel/messages"],
        async onRpc(request) {
            await blockedFetchMessages.promise;
            blockedFetchMessages = Promise.withResolvers();
        },
    });
    await start();
    await openDiscuss(channelId);
    blockedFetchMessages.resolve();
    await waitFor(".o-mail-Message:count(1)");
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelId, fetch_params: { limit: 60, around: 0 } },
        ],
    ]);
    await click("button[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput input:count(1)");
    await editInput(
        document.body,
        ".o-mail-SearchMessageInput .o-mail-SearchInput input",
        "message"
    );
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput.o-searching:count(1)");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput i.oi.oi-spin:count(1)");
    await waitForNone(".o-mail-SearchMessageInput .o-mail-SearchInput i.oi[data-icon='search']");
    blockedFetchMessages.resolve();
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            {
                channel_id: channelId,
                fetch_params: { search_term: "message", before: false },
            },
        ],
    ]);
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(1)");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput:not(.o-searching):count(1)");
    await waitFor(
        ".o-mail-SearchMessageInput .o-mail-SearchInput i.oi[data-icon='search']:count(1)"
    );
    await waitForNone(".o-mail-SearchMessageInput .o-mail-SearchInput i.oi.oi-spin");
});

test.tags("desktop");
test("Clearing message input while pending search should empty message results", async () => {
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
    let blockedFetchMessages = Promise.withResolvers();
    listenStoreFetch("/discuss/channel/messages", {
        logParams: ["/discuss/channel/messages"],
        async onRpc(request) {
            await blockedFetchMessages.promise;
            blockedFetchMessages = Promise.withResolvers();
        },
    });
    await start();
    await openDiscuss(channelId);
    blockedFetchMessages.resolve();
    await waitFor(".o-mail-Message:count(1)");
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            { channel_id: channelId, fetch_params: { limit: 60, around: 0 } },
        ],
    ]);
    await click("button[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput input:count(1)");
    await editInput(
        document.body,
        ".o-mail-SearchMessageInput .o-mail-SearchInput input",
        "This is"
    );
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput.o-searching:count(1)");
    blockedFetchMessages.resolve();
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            {
                channel_id: channelId,
                fetch_params: { search_term: "This is", before: false },
            },
        ],
    ]);
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput:not(.o-searching):count(1)");
    await waitFor(".o-mail-SearchMessageResult .o-mail-Message:count(1)");
    await editInput(
        document.body,
        ".o-mail-SearchMessageInput .o-mail-SearchInput input",
        "This is a message"
    );
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput.o-searching:count(1)");
    await click("button[aria-label='Clear']");
    await contains(".o-mail-SearchMessageInput .o-mail-SearchInput input", { value: "" });
    blockedFetchMessages.resolve();
    await waitStoreFetch([
        [
            "/discuss/channel/messages",
            {
                channel_id: channelId,
                fetch_params: { search_term: "This is a message", before: false },
            },
        ],
    ]);
    await animationFrame();
    await waitForNone(".o-mail-SearchMessageResult .o-mail-Message");
    await contains(".o-mail-SearchMessageInput .o-mail-SearchInput input", { value: "" });
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
    await waitFor(".o-mail-Message:count(1)");
    await click("[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await insertText(".o-mail-SearchMessageInput .o-mail-SearchInput input", "message");
    await waitFor(`.o-mail-SearchMessagesPanel .o-mail-Message .${HIGHLIGHT_CLASS}:count(1)`);
});

test.tags("desktop");
test("Should close the search panel when search button is clicked again", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("[title='Search Messages']");
    await click("[title='Close Search']");
    await waitFor(".o-mail-SearchMessagesPanel:count(1)");
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
    await waitFor(".o-mail-Message:count(30)");
    await click("[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await insertText(".o-mail-SearchMessageInput .o-mail-SearchInput input", "message");
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(30)");
    // give enough time to useVisible to potentially load more (unexpected) messages
    await tick();
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(30)");
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
    await waitFor(".o-mail-Message:count(30)");
    await click("[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await insertText(".o-mail-SearchMessageInput .o-mail-SearchInput input", "message");
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(30)");
    await scroll(".o-mail-SearchMessagesPanel .o-mail-ActionPanel", "bottom");
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(60)");
    // give enough time to useVisible to potentially load more (unexpected) messages
    await tick();
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(60)");
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
    await waitFor(".o-mail-Message:count(1)");
    await click("button[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await insertText(".o-mail-SearchMessageInput .o-mail-SearchInput input", "(message");
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(1)");
});

test.tags("desktop");
test("Search a message containing single quotes", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "<p>I can't do it</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await insertText(".o-mail-SearchMessageInput .o-mail-SearchInput input", "can't");
    await waitFor(".o-mail-SearchMessagesPanel .o-mail-Message:count(1)");
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
    await waitFor(".o-mail-SearchMessagesPanel:count(1)");
    history.back();
    await waitForNone(".o-mail-SearchMessagesPanel");
});

test.tags("desktop");
test("Search should trigger a single store fetch", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "This is a message");
    await click(".o-sendMessageActive:enabled");
    await waitFor(".o-mail-Message:count(1)");
    await click("button[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    listenStoreFetch("/discuss/channel/messages");
    await insertText(".o-mail-SearchMessageInput .o-mail-SearchInput input", "message");
    await waitStoreFetch("/discuss/channel/messages");
    await waitStoreFetch();
});
