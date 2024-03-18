const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";

import { cookie } from "@web/core/browser/cookie";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";
import { browser } from "@web/core/browser/browser";

QUnit.module("livechat service");

test("persisted session history", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv.cookie.set("dgid", guestId);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ guest_id: guestId, fold_state: "open" }),
        ],
        livechat_active: true,
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.adminPartnerId,
    });
    browser.localStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({ threadData: { id: channelId, model: "discuss.channel" }, persisted: true })
    );
    pyEnv["mail.message"].create({
        author_id: pyEnv.adminPartnerId,
        body: "Old message in history",
        res_id: channelId,
        model: "discuss.channel",
        message_type: "comment",
    });
    start();
    await contains(".o-mail-Message-content", { text: "Old message in history" });
});

test("previous operator prioritized", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const userId = pyEnv["res.users"].create({ name: "John Doe", im_status: "online" });
    const previousOperatorId = pyEnv["res.partner"].create({
        name: "John Doe",
        user_ids: [userId],
    });
    pyEnv["im_livechat.channel"].write([livechatChannelId], { user_ids: [Command.link(userId)] });
    cookie.set("im_livechat_previous_operator", JSON.stringify(previousOperatorId));
    start();
    click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message-author", { text: "John Doe" });
});

test("Only necessary requests are made when creating a new chat", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    await start({
        mockRPC(route, args) {
            if (!route.includes("assets")) {
                step(`${route} - ${JSON.stringify(args)}`);
            }
        },
    });
    await contains(".o-livechat-LivechatButton");
    await assertSteps([
        '/web/webclient/load_menus - {"hash":"161803"}', // called because menu_service is loaded in qunit bundle
        `/im_livechat/init - {"channel_id":${livechatChannelId}}`,
    ]);
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
            previous_operator_id: `${pyEnv.adminPartnerId}`,
            temporary_id: -1,
            persisted: true,
        })}`,
        `/mail/action - ${JSON.stringify({
            init_messaging: {
                channel_types: ["livechat"],
            },
            failures: true, // called because mail/core/web is loaded in qunit bundle
            systray_get_activities: true, // called because mail/core/web is loaded in qunit bundle
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
        `/mail/message/post - ${JSON.stringify({
            context: { lang: "en", tz: "taht", uid: serverState.userId, temporary_id: 0.81 },
            post_data: {
                body: "Hello!",
                attachment_ids: [],
                attachment_tokens: [],
                canned_response_ids: [],
                message_type: "comment",
                partner_ids: [],
                subtype_xmlid: "mail.mt_comment",
                partner_emails: [],
                partner_additional_values: {},
            },
            thread_id: threadId,
            thread_model: "discuss.channel",
        })}`,
    ]);
});
