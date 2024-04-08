import { describe, test } from "@odoo/hoot";
import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { rpcWithEnv } from "@mail/utils/common/misc";
import { defineLivechatModels } from "./livechat_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

describe.current.tags("desktop");
defineLivechatModels();

test("Public website visitor is typing", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await openDiscuss(channelId);
    await contains(".o-mail-ThreadIcon .fa.fa-comments");
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    withGuest(guestId, () =>
        rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: channel.id,
        })
    );
    await contains(".o-mail-Discuss-header .o-discuss-Typing-icon");
    await contains(
        ".o-mail-Discuss-header .o-discuss-Typing-icon[title='Visitor 20 is typing...']"
    );
});
