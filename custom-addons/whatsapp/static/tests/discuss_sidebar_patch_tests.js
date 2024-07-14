/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("discuss sidebar (patch)");

QUnit.test("Join whatsapp channels from add channel button", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        {
            name: "WhatsApp 1",
            channel_type: "whatsapp",
        },
        {
            name: "WhatsApp 2",
            channel_type: "whatsapp",
            channel_member_ids: [
                Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            ],
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarCategory-whatsapp .o-mail-DiscussSidebarCategory-add");
    await insertText(".o-discuss-ChannelSelector input", "WhatsApp 2");
    await click(".o-mail-ChannelSelector-suggestion", { text: "WhatsApp 2" });
    await contains(".o-mail-DiscussSidebarChannel", { text: "WhatsApp 2" });
});

QUnit.test(
    "Clicking on cross icon in whatsapp sidebar category item unpins the channel",
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            name: "WhatsApp 1",
            channel_type: "whatsapp",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        await click("div[title='Unpin Conversation']", {
            parent: [
                ".o-mail-DiscussSidebarChannel",
                {
                    contains: [
                        ["span", { text: "WhatsApp 1" }],
                        [".o-mail-ThreadIcon .fa-whatsapp"],
                    ],
                },
            ],
        });
        await contains(".o-mail-DiscussSidebarChannel", {
            count: 0,
            contains: ["span", { text: "WhatsApp 1" }],
        });
        await contains(".o_notification", {
            text: "You unpinned your conversation with WhatsApp 1",
        });
    }
);

QUnit.test("Message unread counter in whatsapp channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [
            Command.create({ message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            ["span", { text: "WhatsApp 1" }],
            [".badge", { text: "1" }],
        ],
    });
});
