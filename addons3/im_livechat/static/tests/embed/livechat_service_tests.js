/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";

import { cookie } from "@web/core/browser/cookie";
import { click, contains, insertText } from "@web/../tests/utils";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { Deferred } from "@web/core/utils/concurrency";

QUnit.module("livechat service");

QUnit.test("persisted session history", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv.cookie.set("dgid", guestId);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.adminPartnerId,
    });
    const [channelInfo] = pyEnv.mockServer._mockDiscussChannelChannelInfo([channelId]);
    cookie.set("im_livechat_session", JSON.stringify(channelInfo));
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

QUnit.test("previous operator prioritized", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const userId = pyEnv["res.users"].create({ name: "John Doe", im_status: "online" });
    const previousOperatorId = pyEnv["res.partner"].create({ user_ids: [userId] });
    pyEnv["im_livechat.channel"].write([livechatChannelId], { user_ids: [Command.link(userId)] });
    cookie.set("im_livechat_previous_operator_pid", JSON.stringify(previousOperatorId));
    start();
    click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message-author", { text: "John Doe" });
});

QUnit.test("Only necessary requests are made when creating a new chat", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    const linkPreviewDeferred = new Deferred();
    await start({
        mockRPC(route) {
            if (!route.includes("assets")) {
                assert.step(route);
            }
            if (route === "/mail/link_preview") {
                linkPreviewDeferred.resolve();
            }
        },
    });
    await contains(".o-livechat-LivechatButton");
    assert.verifySteps([
        "/im_livechat/init",
        "/web/webclient/load_menus", // called because menu_service is loaded in qunit bundle
        "/mail/load_message_failures", // called because mail/core/web is loaded in qunit bundle
    ]);
    await click(".o-livechat-LivechatButton");
    assert.verifySteps(["/im_livechat/get_session"]);
    await insertText(".o-mail-Composer-input", "Hello!");
    assert.verifySteps([]);
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello!" });
    await linkPreviewDeferred;
    assert.verifySteps([
        "/im_livechat/get_session",
        "/mail/init_messaging",
        "/mail/message/post",
        "/mail/link_preview",
    ]);
});
