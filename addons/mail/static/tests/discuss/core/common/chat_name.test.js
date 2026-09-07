import {
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("Chat name keeps both persons when a member is gone", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Alice" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
        name: "Mitchell Admin, Alice",
    });
    // Simulate the deletion of the correspondent, e.g. along with their partner.
    pyEnv["discuss.channel.member"].unlink(
        pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["partner_id", "=", partnerId],
        ])
    );
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-headerContent .o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice']"
    );
});
