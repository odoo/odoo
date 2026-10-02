import {
    actionPanel,
    click,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Opening Pinned Messages Panel twice from notification only needs one click to close", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Test Partner" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, login: "abcd" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Message to pin",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await withUser(userId, () =>
        pyEnv["discuss.channel"].set_message_pin(channelId, messageId, true)
    );
    await start();
    await openDiscuss(channelId);
    await click("a[data-oe-type='pin-menu']");
    await waitFor(`${actionPanel("Pinned Messages")}:count(1)`);
    await click("a[data-oe-type='pin-menu']");
    await waitFor(`${actionPanel("Pinned Messages")}:count(1)`);
    await click("button[name='pinned-messages'].active");
    await waitForNone(actionPanel("Pinned Messages"));
});
