import { describe, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import {
    click,
    contains,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("message translation in livechat (agent is member)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Mario" }),
                livechat_member_type: "visitor",
            }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Mai mettere l'ananas sulla pizza!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click("[title='Expand']");
    await contains(".o-dropdown-item:contains('Translate')");
});

test("message translation in livechat (agent is not member)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Mario" }),
                livechat_member_type: "visitor",
            }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Mai mettere l'ananas sulla pizza!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click("[title='Expand']");
    await contains(".o-dropdown-item:contains('Translate')");
});

test("click 'translate' on message prompts for auto-translate of new messages", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: guestId,
                livechat_member_type: "visitor",
            }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Mai mettere l'ananas sulla pizza!",
        model: "discuss.channel",
        res_id: channelId,
    });
    onRpcBefore("/mail/message/translate", ({ message_id }) => {
        const [message] = pyEnv["mail.message"].search_read([["id", "=", message_id]]);
        if (message.body === "Mai mettere l'ananas sulla pizza!") {
            return {
                body: "Never put pineapple on pizza!",
                lang_name: "Italian",
                error: null,
            };
        }
        if (message.body === "Il tempo è bello oggi.") {
            return {
                body: "The weather is nice today!",
                lang_name: "Italian",
                error: null,
            };
        }
        return {
            body: "Oh, the weather has changed.",
            lang_name: "Italian",
            error: null,
        };
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click("[title='Expand']");
    await click(".o-dropdown-item:contains('Translate')");
    await contains(".o_notification_body span:contains('Auto-translate newer messages?')");
    await click(".o_notification_body button:contains('Enable')");
    await withGuest(guestId, async () => {
        await rpc("/mail/message/post", {
            post_data: {
                body: "Il tempo è bello oggi.",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
    });
    await contains(
        ".o-mail-Message-body:text('Never put pineapple on pizza! (Translated from: Italian)')"
    );
    await contains(
        ".o-mail-Message-body:text('The weather is nice today! (Translated from: Italian)')"
    );
    await click("[title='Expand']", {
        target: queryAll(
            ".o-mail-Message:contains('The weather is nice today! (Translated from: Italian)')"
        )[0],
    });
    await click(".o-dropdown-item:contains('Revert')");
    await contains(".o_notification_body span:contains('Cancel auto-translate?')");
    await click(".o_notification_body button:contains('Disable')");

    await withGuest(guestId, async () => {
        await rpc("/mail/message/post", {
            post_data: {
                body: "Ach, il tempo è cambiato.",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
    });
    await contains(".o-mail-Message-body:text('Ach, il tempo è cambiato.')");
});
