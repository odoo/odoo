import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";
import { url } from "@web/core/utils/urls";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { defineWebsiteLivechatModels } from "@website_livechat/../tests/website_livechat_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("Discuss header shows visitor avatar", async () => {
    const pyEnv = await startServer();
    const visitorId = pyEnv["website.visitor"].create({});
    const guestId = pyEnv["mail.guest"].create({ name: `Visitor #${visitorId}` });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    const [guest] = pyEnv["mail.guest"].search_read([["id", "=", guestId]]);
    await contains(
        `.o-mail-DiscussContent-header img[data-src='${url(
            `/web/image/mail.guest/${guestId}/avatar_128?unique=${
                deserializeDateTime(guest.write_date).ts
            }`
        )}']`
    );
});
