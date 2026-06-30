import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
    postLivechatMessage,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    assertChatBubbleAndWindowImStatus,
    click,
    contains,
    inputFiles,
    mockGetMedia,
    onRpcBefore,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { 
    Command, 
    patchWithCleanup,
    serverState, 
    withUser 
} from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { getOrigin } from "@web/core/utils/urls";
import { session } from "@web/session";

describe.current.tags("desktop");
defineLivechatModels();

test("internal users can upload file to temporary thread", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const [partnerUser] = pyEnv["res.users"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: partnerUser, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await contains(".o-mail-Composer");
    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Attach files')");
    await inputFiles(".o-mail-Composer .o_input_file", [file]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)");
    const subscribed = waitUntilSubscribe();
    await triggerHotkey("Enter");
    await subscribed;
    await contains(".o-mail-Message .o-mail-AttachmentContainer:contains(text.txt)");
});

test("The name of the conversation changes based on the agents' names", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    const operatorUserId = serverState.userId;
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp" });
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello World!");
    await subscribed;
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([["guest_id", "=", pyEnv.cookie.get("dgid")]]),
        ],
    ]);
    const userId = pyEnv["res.users"].create({
        name: "James",
    });
    pyEnv["res.partner"].create({
        lang: "en",
        name: "James",
        user_ids: [userId],
    });
    // Adding a member is reserved to logged-in users: simulate the operator adding the agent,
    // which notifies the visitor through the bus (a guest cannot call add_members themselves).
    await withUser(operatorUserId, () =>
        rpc("/mail/store", {
            fetch_params: [
                ["/discuss/channel/add_members", { channel_id: channelId, user_ids: [userId] }],
            ],
        })
    );
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp, James" });
});

test("Portal users should not be able to start a call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const joelUid = pyEnv["res.users"].create({
        name: "Joel",
        share: true,
        login: "joel",
        password: "joel",
    });
    const joelPid = pyEnv["res.partner"].create({
        name: "Joel",
        user_ids: [joelUid],
    });
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: { login: "joel", password: "joel" }, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header:text('MitchellOp')");
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello MitchellOp!");
    await subscribed;
    await contains(".o-mail-Message[data-persistent]:contains('Hello MitchellOp!')");
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button", { count: 2 });
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title='Fold']");
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title*='Close']");
    await contains(".o-discuss-Call", { count: 0 });
    // simulate operator starts call
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([["partner_id", "=", joelPid]]),
        ],
    ]);
    await withUser(serverState.userId, () =>
        rpc("/mail/rtc/channel/join_call", { channel_id: channelId }, { silent: true })
    );
    await contains(".o-discuss-Call button", { count: 2 });
    await contains(".o-discuss-Call button[title='Join Video Call']");
    await contains(".o-discuss-Call button[title='Join Call']");
    // still same actions in header
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button", { count: 2 });
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title='Fold']");
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title*='Close']");
});

test("avatar url contains access token for non-internal users", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    const [partner] = pyEnv["res.partner"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(
        `.o-mail-ChatWindow-threadAvatar img[data-src="${getOrigin()}/web/image/res.partner/${
            partner.id
        }/avatar_128?access_token=${partner.id}&unique=${
            deserializeDateTime(partner.write_date).ts
        }"]`
    );
    await contains(
        `.o-mail-Message-avatar[data-src="${getOrigin()}/web/image/res.partner/${
            partner.id
        }/avatar_128?access_token=${partner.id}&unique=${
            deserializeDateTime(partner.write_date).ts
        }"]`
    );
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello World!");
    await subscribed;
    const guestId = pyEnv.cookie.get("dgid");
    const [guest] = pyEnv["mail.guest"].read(guestId);
    await contains(
        `.o-mail-Message-avatar[data-src="${getOrigin()}/web/image/mail.guest/${
            guest.id
        }/avatar_128?access_token=${guest.id}&unique=${deserializeDateTime(guest.write_date).ts}"]`
    );
});

test("can close confirm livechat with keyboard", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore((route) => {
        if (route === "/im_livechat/visitor_leave_session") {
            expect.step(route);
        }
    });
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello");
    await subscribed;
    await contains(".o-mail-Thread:not([data-transient])");
    await triggerHotkey("Escape");
    await contains(
        ".o-livechat-CloseConfirmation:has(:text('Leaving will end the live chat with Mitchell Admin. Are you sure you want to continue?'))"
    );
    await triggerHotkey("Escape");
    await contains(".o-livechat-CloseConfirmation", { count: 0 });
    await triggerHotkey("Escape");
    await contains(
        ".o-livechat-CloseConfirmation:has(:text('Leaving will end the live chat with Mitchell Admin. Are you sure you want to continue?'))"
    );
    await triggerHotkey("Enter");
    await expect.waitForSteps(["/im_livechat/visitor_leave_session"]);
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
});

test("Should not show IM status of agents", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const joelUid = pyEnv["res.users"].create({
        name: "Joel",
        share: true,
        login: "joel",
        password: "joel",
    });
    pyEnv["res.partner"].create({ name: "Joel", user_ids: [joelUid] });
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: { login: "joel", password: "joel" }, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header:text('MitchellOp')");
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello MitchellOp!");
    await subscribed;
    await contains(".o-mail-Message[data-persistent]:contains('Hello MitchellOp!')");
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-ChatBubble");
    await assertChatBubbleAndWindowImStatus("MitchellOp", 0);
});

test("Displays the name of agent in welcome message", async () => {
    const pyEnv = await startServer();
    const agentId = pyEnv["res.partner"].create({
        name: "Jane",
        user_ids: [Command.create({ name: "jane" })],
    });
    const botId = pyEnv["res.partner"].create({
        name: "Bot",
        user_ids: [Command.create({ name: "bot" })],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 2" });
    const livechatChannelId = await loadDefaultEmbedConfig();
    patchWithCleanup(session, {
        livechatData: {
            ...session.livechatData,
            options: {
                ...session.livechatData?.options,
                default_message: "Hello, how may I help you?",
            },
        },
    });
    const [chatAsAgent, chatAsBot] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: agentId, livechat_member_type: "agent" }),
                Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
            ],
            livechat_channel_id: livechatChannelId,
            channel_type: "livechat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: botId, livechat_member_type: "bot" }),
                Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
            ],
            livechat_channel_id: livechatChannelId,
            channel_type: "livechat",
        },
    ]);
    setupChatHub({ opened: [chatAsAgent, chatAsBot] });
    await start({ authenticateAs: false });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(
        ".o-mail-ChatWindow:eq(0) .o-mail-Message:has(:text('Hello, how may I help you?')) .o-mail-Message-author:text('Jane')"
    );
    await contains(
        ".o-mail-ChatWindow:eq(1) .o-mail-Message:has(:text('Hello, how may I help you?')) .o-mail-Message-author:text('Bot')"
    );
});

