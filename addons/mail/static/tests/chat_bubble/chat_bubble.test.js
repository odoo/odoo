import { describe, expect, test } from "@odoo/hoot";
import { hover, leave } from "@odoo/hoot-dom";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    openFormView,
    onRpcBefore,
    patchUiSize,
    start,
    startServer,
    triggerHotkey,
} from "../mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";
import { rpcWithEnv } from "@mail/utils/common/misc";

describe.current.tags("desktop");
defineMailModels();

test("Active conversations are displayed as bubbles.", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "Channel A",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
        {
            name: "Channel B",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
    ]);
    await start();
    await contains(".o-mail-ChatBubble", { count: 2 });
    await click(".o-mail-ChatBubble", { count: 2 });
    await contains(".o-mail-ChatBubble", { count: 1 });
    await contains(".o-mail-ChatWindow", { count: 1 });
});

test("Threadless windows don't count as bubbles. [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await contains(".o-mail-ChatWindow", { count: 1 });
    // No thread was selected, hence no bubble is created.
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatBubble", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "John");
    await click(".o-discuss-ChannelSelector-suggestion");
    triggerHotkey("Enter");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Thread-empty", { text: "There are no messages in this conversation." });
    // A thread was selected, it is considered an active conversation.
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatBubble", { count: 1 });
});

test("Active conversations are never duplicated. [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    // Make conversation active.
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "John");
    await click(".o-discuss-ChannelSelector-suggestion");
    triggerHotkey("Enter");
    // Turn it into a bubble.
    await contains(".o-mail-Thread-empty", { text: "There are no messages in this conversation." });
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatBubble", { count: 1 });
    // Duplication attempt.
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "John");
    await click(".o-discuss-ChannelSelector-suggestion");
    triggerHotkey("Enter");
    // The chat window opens and the bubble is removed.
    await contains(".o-mail-ChatBubble", { count: 0 });
    await click(".o-mail-ChatWindow-command[title='Fold']");
    // Behavior is consistent with previous tests even with the messaging menu.
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatBubble", { count: 0 });
});

test("Chat bubbles do not overflow and remain reachable.", async () => {
    const pyEnv = await startServer();
    for (let i = 1; i <= 8; i++) {
        pyEnv["discuss.channel"].create({
            name: String(i),
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        });
    }
    await start();
    // Limited to 7 bubbles.
    for (let i = 8; i > 1; i--) {
        await contains(`.o-mail-ChatBubble[name='${String(i)}']`);
    }
    await contains(".o-mail-ChatBubble[name='1']", { count: 0 });
    await contains(".o-mail-ChatBubbleHidden-btn", { text: "+1" });
    await click(".o-mail-ChatBubbleHidden-btn");
    await contains(".o-mail-ChatBubbleHidden-item[name='1']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o-mail-ChatBubbleHidden-item");
    await contains(".o-mail-ChatWindow", { count: 1 });
    await contains(".o-mail-ChatBubbleHidden-btn", { count: 0 });
});

test("Ordering of chat bubbles is consistent and seems logical.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            Command.create({ fold_state: "folded", partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    for (let i = 1; i <= 7; i++) {
        pyEnv["discuss.channel"].create({
            name: String(i),
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        });
    }
    const env = await start();
    rpc = rpcWithEnv(env);
    // The most recent conversation appears first.
    await contains(":nth-child(1 of .o-mail-ChatBubble)[name='7']");
    await contains(":nth-child(2 of .o-mail-ChatBubble)[name='6']");
    await contains(":nth-child(3 of .o-mail-ChatBubble)[name='5']");
    await contains(":nth-child(4 of .o-mail-ChatBubble)[name='4']");
    await contains(":nth-child(5 of .o-mail-ChatBubble)[name='3']");
    await contains(":nth-child(6 of .o-mail-ChatBubble)[name='2']");
    await contains(":nth-child(7 of .o-mail-ChatBubble)[name='1']");
    // Oldest conversation is hidden because of the Soft limit.
    await contains(".o-mail-ChatBubble[name='Demo']", { count: 0 });
    await click(".o-mail-ChatBubble[name='3']");
    // Oldest conversation takes the free spot and is now displayed last.
    await contains(":nth-child(7 of .o-mail-ChatBubble)[name='Demo']");
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatBubble[name='Demo']", { count: 0 });
    await click(".o-mail-ChatBubble[name='4']");
    await contains(":nth-child(1 of .o-mail-ChatBubble)[name='3']");
    await contains(":nth-child(2 of .o-mail-ChatBubble)[name='7']");
    await contains(":nth-child(3 of .o-mail-ChatBubble)[name='6']");
    await contains(":nth-child(7 of .o-mail-ChatBubble)[name='Demo']");
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    // Receiving a message does not alter the order.
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "test", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await click(".o-mail-ChatBubbleHidden-btn");
    await contains(".o-mail-ChatBubbleHidden-item[name='Demo']");
});

test("Hovering chat bubbles displays previews.", async () => {
    const pyEnv = await startServer();
    const marcPartnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const marcChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            Command.create({ fold_state: "folded", partner_id: marcPartnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        body: "Hello!",
        model: "discuss.channel",
        author_id: marcPartnerId,
        res_id: marcChannelId,
    });
    const demoPartnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const demoChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            Command.create({ fold_state: "folded", partner_id: demoPartnerId }),
        ],
        channel_type: "chat",
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    // Hovering a bubble with a non-empty thread displays a preview with the last message.
    await contains(".o-mail-ChatBubble[name='Marc']");
    await hover(".o-mail-ChatBubble[name='Marc']")
    await contains(".o-mail-ChatBubblePreview p", { text: "Marc: Hello!" });
    await leave(".o-mail-ChatBubble[name='Marc']")
    await contains(".o-mail-ChatBubblePreview", { count: 0 });
    // No messages in the thread and no preview displayed
    await hover(".o-mail-ChatBubble[name='Demo']")
    await contains(".o-mail-ChatBubblePreview", { count: 0 });
    await leave(".o-mail-ChatBubble[name='Demo']")
    rpc("/mail/message/post", {
        post_data: { body: "Hi", message_type: "comment" },
        thread_id: demoChannelId,
        thread_model: "discuss.channel",
    })
    await hover(".o-mail-ChatBubble[name='Demo']")
    await contains(".o-mail-ChatBubblePreview p", { text: "You: Hi" });
});

test("Chat bubbles behavior is mirrored if there are multiple browser tabs.", async () => {
    const pyEnv = await startServer();
    const marcPartnerId = pyEnv["res.partner"].create({ name: "Marc" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            Command.create({ fold_state: "folded", partner_id: marcPartnerId }),
        ],
        channel_type: "chat",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    // Opening a chat window opens the same window on the second tab.
    await contains(".o-mail-ChatBubble", { target: tab1.target });
    await contains(".o-mail-ChatBubble", { target: tab2.target });
    await click(".o-mail-ChatBubble[name='Marc']", { target: tab1.target });
    await contains(".o-mail-ChatWindow", { target: tab2.target });
    // Window is folded on both tabs.
    await click(".o-mail-ChatWindow-command[title='Fold']", { target: tab2.target });
    await contains(".o-mail-ChatWindow", { target: tab1.target, count: 0 });
    // Bubble is closed on both tabs.
    await click(".o-mail-ChatBubble[name='Marc'] .o-mail-ChatBubble-close", {
        target: tab1.target,
    });
    await contains(".o-mail-ChatBubble[name='Marc']", {
        target: tab2.target,
        count: 0,
    });
});

test("Open a chat window triggers message fetching", async (assert) => {
    const pyEnv = await startServer();
    const [channeId1, channelId2] = pyEnv["discuss.channel"].create([
        {
            name: "Orange",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
        {
            name: "Apple",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
    ]);
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
    ]);
    onRpcBefore("/discuss/channel/messages", (args) => {
        expect.step("fetch_messages");
    });
    await start();
    await click(".o-mail-ChatBubble[name='Orange']");
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-Message-content", { text: "Orange" });
    // This one remains closed, so it does not trigger fetching.
    await contains(".o-mail-Message-content", { count: 0, text: "Apple" });
    expect(["fetch_messages"]).toVerifySteps();
});

test("If there is not enough space, windows are replaced", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "Orange",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
        {
            name: "Apple",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
        {
            name: "Banana",
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        },
    ]);
    patchUiSize({ width: 900 });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 2 + CHAT_WINDOW_INBETWEEN_WIDTH
    ).toBeLessThan(900);
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeGreaterThan(900);
    await start();
    await click(".o-mail-ChatBubble[name='Orange']");
    await click(".o-mail-ChatBubble[name='Banana']");
    await contains(".o-mail-ChatWindow", { count: 2 });
    await click(".o-mail-ChatBubble[name='Apple']");
    await contains(".o-mail-ChatBubble[name='Banana']");
    await contains(".o-mail-ChatWindow", { text: "Apple" });
});

test("bubbles are not displayed over Discuss. [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            Command.create({ fold_state: "folded", partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    // Sending a message in Discuss adds a bubble.
    await openDiscuss(chatId);
    await insertText(".o-mail-Composer-input", "add");
    await click(".o-mail-Composer-send:enabled");
    await openFormView("discuss.channel", chatId);
    await click(".o-mail-ChatBubble[name='Marc']");
    // If a bubble or window already exists, it is not duplicated.
    await openDiscuss(chatId);
    await insertText(".o-mail-Composer-input", "duplicate");
    await click(".o-mail-Composer-send:enabled");
    await openFormView("discuss.channel", chatId);
    // Receiving a message also adds a bubble.
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command[title='Close Chat Window']");
    await openDiscuss(channelId);
    await contains(".o-mail-ChatWindow", { count: 0 });
    await withUser(userId, () => {
        rpc("/mail/message/post", {
                post_data: { body: "new message", message_type: "comment" },
                thread_id: chatId,
                thread_model: "discuss.channel",
            });
    });
    await openFormView("discuss.channel", chatId);
    // TODO: FIX THIS
    // await contains(".o-mail-ChatBubble[name='Marc']"); 
});

test("Overflowing bubbles are hidden.", async () => {
    const pyEnv = await startServer();
    for (let i = 1; i <= 8; i++) {
        pyEnv["discuss.channel"].create({
            name: String(i),
            channel_member_ids: [
                Command.create({ fold_state: "folded", partner_id: serverState.partnerId }),
            ],
        });
    }
    const env = await start();
    rpc = rpcWithEnv(env);
    // Conversation can be opened from the hidden list.
    await click(".o-mail-ChatBubbleHidden-btn");
    await contains(".o-mail-ChatBubbleHidden");
    await click(".o-mail-ChatBubbleHidden-item");
    await contains(".o-mail-ChatBubbleHidden", { count: 0 });
    await contains(".o-mail-ChatBubbleHidden-btn", { count: 0 });
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command[title='Fold']");
    // Hidden conversation can be opened from the messaging menu.
    await click("i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "2" });
    await contains(".o-mail-ChatBubbleHidden", { count: 0 });
    await contains(".o-mail-ChatBubbleHidden-btn", { count: 0 });
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command[title='Fold']");
    // Close conversation from the hidden menu.
    await click(".o-mail-ChatBubbleHidden-btn");
    await hover(".o-mail-ChatBubbleHidden-item")
    await click(".o-mail-ChatBubbleHidden-close");
    await contains(".o-mail-ChatBubbleHidden", { count: 0 });
    await contains(".o-mail-ChatBubbleHidden-btn", { count: 0 });
    await contains(".o-mail-ChatWindow", { count: 0 });
});
