import { describe, test } from "@odoo/hoot";
import { contains, defineMailModels, start, startServer } from "../mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("openChat: display notification for partner without user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const env = await start();
    await env.services["mail.store"].openChat({ partnerId });
    await contains(".o_notification:has(.o_notification_bar.bg-info)", {
        text: "You can only chat with partners that have a dedicated user.",
    });
});

test("openChat: display notification for wrong user", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].create({});
    const env = await start();
    // userId not in the server data
    await env.services["mail.store"].openChat({ userId: 4242 });
    await contains(".o_notification:has(.o_notification_bar.bg-warning)", {
        text: "You can only chat with existing users.",
    });
});

test("openChat: open new chat for user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    const env = await start();
    await contains(".o-mail-ChatWindowContainer");
    await contains(".o-mail-ChatWindow", { count: 0 });
    env.services["mail.store"].openChat({ partnerId });
    await contains(".o-mail-ChatWindow");
});

test("openChat: open existing chat for user [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                fold_state: "open",
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const env = await start();
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:not(:focus)");
    env.services["mail.store"].openChat({ partnerId });
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:focus");
});
