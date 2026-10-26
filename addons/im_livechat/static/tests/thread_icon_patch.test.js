import { openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { getOrigin } from "@web/core/utils/urls";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Public website visitor is typing", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        avatar_cache_key: "abc123",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    await start();
    await openDiscuss(channelId);
    // thread avatar of public visitors should be visible in the header
    await waitFor(
        `.o-mail-DiscussContent-header img[data-src='${getOrigin()}/web/image/discuss.channel/${channelId}/avatar_128?unique=abc123']:count(1)`
    );
    await waitFor(".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='circle']:count(1)");
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    withGuest(guestId, () =>
        rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: channel.id,
        })
    );
    await waitFor(".o-mail-DiscussContent-header .o-discuss-Typing-icon:count(1)");
    await waitFor(
        ".o-mail-DiscussContent-header .o-discuss-Typing-icon[title='Visitor 20 is typing...']:count(1)"
    );
});
