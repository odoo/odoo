const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("chat window (patch)");

test("closing a chat window with no message from admin side unpins it", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                is_pinned: true,
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        uuid: "channel-10-uuid",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o-mail-ChatWindow-command[title='Close Chat Window']");
    await contains(".o_notification", { text: "You unpinned your conversation with Demo" });
});
