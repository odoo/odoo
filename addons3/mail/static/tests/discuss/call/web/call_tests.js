/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("call");

QUnit.test("no default rtc after joining a chat conversation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    openDiscuss();
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Discuss-content .o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});

QUnit.test("no default rtc after joining a group conversation", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const { openDiscuss } = await start();
    openDiscuss();
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await click(".o-discuss-ChannelSelector-suggestion", { text: "Mario" });
    await insertText(".o-discuss-ChannelSelector input", "luigi", { replace: true });
    await click(".o-discuss-ChannelSelector-suggestion", { text: "Luigi" });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Discuss-content .o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});
