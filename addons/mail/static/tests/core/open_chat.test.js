import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { Command, getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("openChat: display notification for partner without user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await getService("mail.store").openChat({ partnerId });
    await waitFor(
        ".o_notification:has(.o_notification_bar.bg-info):text('You can only chat with partners that have a dedicated user.'):count(1)"
    );
});

test("openChat: display notification for wrong user", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].create({});
    await start();
    // userId not in the server data
    await getService("mail.store").openChat({ userId: 4242 });
    await waitFor(
        ".o_notification:has(.o_notification_bar.bg-warning):text('You can only chat with existing users.'):count(1)"
    );
});

test("openChat: open new chat for user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await waitFor(".o-mail-ChatHub:count(1)");
    await waitForNone(".o-mail-ChatWindow");
    getService("mail.store").openChat({ partnerId });
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test.tags("focus required");
test("openChat: open existing chat for user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    getService("mail.store").openChat({ partnerId });
    await waitFor(".o-mail-ChatWindow .o-mail-Composer-html:focus:count(1)");
});
