import { Command, serverState } from "@web/../tests/web_test_helpers";
import { click, contains } from "@mail/../tests/mail_test_helpers_contains";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { setupChatHub, start, startServer } from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");

defineLivechatModels();
test("Do not open chat windows automatically when chat hub is compact", async () => {
    const pyEnv = await startServer();
    setupChatHub({ folded: [pyEnv["discuss.channel"].create({ name: "General" })] });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    await start();
    await click("button[title='Chat Options']");
    await click(".o-dropdown-item", { text: "Hide all conversations" });
    await contains(".o-mail-ChatHub-bubbleBtn .fa-comments");
    await withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "I need help!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatHub-bubbleBtn .badge", { text: "1" });
    await click("button.o-mail-ChatHub-bubbleBtn");
    await contains(".o-mail-ChatBubble[name=Visitor] .badge", { text: "1" });
    await contains(".o-mail-ChatWindow", { count: 0, text: "Visitor" });
    await click(".o-mail-ChatBubble[name=Visitor] .o-mail-ChatHub-bubbleBtn");
    await contains(".o-mail-ChatWindow", { text: "Visitor" });
});
