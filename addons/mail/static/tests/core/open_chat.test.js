import {
    contains,
    defineMailModels,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("openChat: display notification for partner without user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await getService("mail.store").openChat({ partnerId });
    await contains(".o_notification:has(.o_notification_bar.bg-info)", {
        text: "You can only chat with partners that have a dedicated user.",
    });
});

test("openChat: display notification for wrong user", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].create({});
    await start();
    // userId not in the server data
    await getService("mail.store").openChat({ userId: 4242 });
    await contains(".o_notification:has(.o_notification_bar.bg-warning)", {
        text: "You can only chat with existing users.",
    });
});

test("openChat: open new chat for user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await contains(".o-mail-ChatHub");
    await contains(".o-mail-ChatWindow", { count: 0 });
    getService("mail.store").openChat({ partnerId });
    await contains(".o-mail-ChatWindow");
});

test.tags("focus required");
test("openChat: open existing chat for user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:not(:focus)");
    getService("mail.store").openChat({ partnerId });
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:focus");
});
