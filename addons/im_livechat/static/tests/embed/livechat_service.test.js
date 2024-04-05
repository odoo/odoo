import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
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
import { Command, mountWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";

describe.current.tags("desktop");
defineLivechatModels();

test("persisted session history", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId, fold_state: "open" }),
        ],
        livechat_active: true,
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    browser.localStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({ threadData: { id: channelId, model: "discuss.channel" }, persisted: true })
    );
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Old message in history",
        res_id: channelId,
        model: "discuss.channel",
        message_type: "comment",
    });
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await mountWithCleanup(LivechatButton);
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
    cookie.set("im_livechat_previous_operator", JSON.stringify(previousOperatorId));
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message-author", { text: "John Doe" });
});

test("Only necessary requests are made when creating a new chat", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    onRpcBefore((route, args) => {
        if (!route.includes("assets")) {
            step(`${route} - ${JSON.stringify(args)}`);
        }
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await contains(".o-livechat-LivechatButton");
    await assertSteps([`/im_livechat/init - {"channel_id":${livechatChannelId}}`]);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([
        `/im_livechat/get_session - ${JSON.stringify({
            channel_id: livechatChannelId,
            anonymous_name: "Visitor",
            persisted: false,
        })}`,
    ]);
    await insertText(".o-mail-Composer-input", "Hello!");
    await assertSteps([]);
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello!" });
    const [threadId] = pyEnv["discuss.channel"].search([], { order: "id DESC" });
    await assertSteps([
        `/im_livechat/get_session - ${JSON.stringify({
            channel_id: livechatChannelId,
            anonymous_name: "Visitor",
            previous_operator_id: serverState.partnerId.toString(),
            temporary_id: -1,
            persisted: true,
        })}`,
        `/mail/action - ${JSON.stringify({
            init_messaging: {
                channel_types: ["livechat"],
            },
            failures: true, // called because mail/core/web is loaded in test bundle
            systray_get_activities: true, // called because mail/core/web is loaded in test bundle
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
        `/mail/message/post - ${JSON.stringify({
            context: {
                lang: "en",
                tz: "taht",
                uid: serverState.userId,
                allowed_company_ids: [1],
                temporary_id: 0.81,
            },
            post_data: {
                body: "Hello!",
                attachment_ids: [],
                message_type: "comment",
                partner_ids: [],
                subtype_xmlid: "mail.mt_comment",
            },
            attachment_tokens: [],
            canned_response_ids: [],
            partner_emails: [],
            partner_additional_values: {},
            thread_id: threadId,
            thread_model: "discuss.channel",
        })}`,
        `/discuss/channel/info - ${JSON.stringify({ channel_id: 1 })}`, // called because mail/core/web is loaded in test bundle
    ]);
});
