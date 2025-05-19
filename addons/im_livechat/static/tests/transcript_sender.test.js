import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { contains, focus, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";

describe.current.tags("desktop");
defineLivechatModels();

test("agent can send conversation after livechat ends", async () => {
    const pyEnv = await startServer();
    const demoPartnerId = pyEnv["res.partner"].create({
        name: "Awesome partner",
        email: "awesome@example.com",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: demoPartnerId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_end_dt: serializeDate(today()),
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await focus("input[placeholder='mail@example.com']", { value: "awesome@example.com" });
    await press("Enter");
    await contains(".form-text", { text: "The conversation was sent." });
});
