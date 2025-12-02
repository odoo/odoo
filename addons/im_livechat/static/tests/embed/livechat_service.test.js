import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import {
    click,
    contains,
    insertText,
    listenStoreFetch,
    onRpcBefore,
    setupChatHub,
    start,
    startServer,
    STORE_FETCH_ROUTES,
    triggerHotkey,
    userContext,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import {
    asyncStep,
    Command,
    onRpc,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("persisted session history", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    expirableStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({
            store: { "discuss.channel": [{ id: channelId }] },
            persisted: true,
            livechatUserId: serverState.publicUserId,
        })
    );
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Old message in history",
        res_id: channelId,
        model: "discuss.channel",
        message_type: "comment",
    });
    setupChatHub({ opened: [channelId] });
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await contains(".o-mail-Message-content", { text: "Old message in history" });
});

test("previous operator prioritized", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const userId = pyEnv["res.users"].create({ name: "John Doe", im_status: "online" });
    const previousOperatorId = pyEnv["res.partner"].create({
        name: "John Doe",
        user_ids: [userId],
    });
    pyEnv["im_livechat.channel"].write([livechatChannelId], { user_ids: [Command.link(userId)] });
    expirableStorage.setItem("im_livechat_previous_operator", JSON.stringify(previousOperatorId));
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message-author", { text: "John Doe" });
});

test("Only necessary requests are made when creating a new chat", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const operatorPartnerId = serverState.partnerId;
    onRpcBefore((route, args) => {
        if (!route.includes("assets") && !STORE_FETCH_ROUTES.includes(route)) {
            asyncStep(`${route} - ${JSON.stringify(args)}`);
        }
    });
    listenStoreFetch(undefined, { logParams: ["init_livechat"] });
    await start({ authenticateAs: false });
    await contains(".o-livechat-LivechatButton");
    await waitStoreFetch([
        "failures", // called because mail/core/web is loaded in test bundle
        "systray_get_activities", // called because mail/core/web is loaded in test bundle
        "init_messaging",
        ["init_livechat", livechatChannelId],
    ]);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await waitForSteps([
        `/im_livechat/get_session - ${JSON.stringify({
            channel_id: livechatChannelId,
            previous_operator_id: null,
            persisted: false,
        })}`,
    ]);
    await insertText(".o-mail-Composer-input", "Hello!");
    await waitForSteps([]);
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello!" });
    const [threadId] = pyEnv["discuss.channel"].search([], { order: "id DESC" });
    await waitStoreFetch(
        [
            "failures", // called because mail/core/web is loaded in test bundle
            "systray_get_activities", // called because mail/core/web is loaded in test bundle
            "init_messaging",
        ],
        {
            stepsBefore: [
                `/im_livechat/get_session - ${JSON.stringify({
                    channel_id: livechatChannelId,
                    previous_operator_id: operatorPartnerId,
                    persisted: true,
                })}`,
                `/mail/message/post - ${JSON.stringify({
                    post_data: {
                        body: "Hello!",
                        email_add_signature: true,
                        message_type: "comment",
                        subtype_xmlid: "mail.mt_comment",
                    },
                    thread_id: threadId,
                    thread_model: "discuss.channel",
                    context: { ...userContext(), temporary_id: 0.8200000000000001 },
                })}`,
            ],
        }
    );
});

test("do not create new thread when operator answers to visitor", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    onRpc("/im_livechat/get_session", async () => asyncStep("/im_livechat/get_session"));
    onRpc("/mail/message/post", async () => asyncStep("/mail/message/post"));
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    setupChatHub({ opened: [channelId] });
    await start({
        authenticateAs: pyEnv["res.users"].search_read([["id", "=", serverState.userId]])[0],
    });
    await insertText(".o-mail-Composer-input", "Hello!");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello!" });
    await waitForSteps(["/mail/message/post"]);
});
