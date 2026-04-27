import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineWhatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

describe.current.tags("desktop");
defineWhatsAppModels();

test("Join whatsapp channels from add channel button", async () => {
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
                Command.create({
                    unpin_dt: "2021-01-01 12:00:00",
                    last_interest_dt: "2021-01-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
            ],
        },
    ]);
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarCategory-whatsapp .o-mail-DiscussSidebarCategory-add");
    await insertText(".o-discuss-ChannelSelector input", "WhatsApp 2");
    await click(".o-mail-ChannelSelector-suggestion", { text: "WhatsApp 2" });
    await contains(".o-mail-DiscussSidebarChannel", { text: "WhatsApp 2" });
});

test("Clicking on cross icon in whatsapp sidebar category item unpins the channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss();
    await click("[title='Unpin Conversation']", {
        parent: [
            ".o-mail-DiscussSidebarChannel",
            {
                contains: [["span", { text: "WhatsApp 1" }], [".o-mail-ThreadIcon .fa-whatsapp"]],
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
});

test("Message unread counter in whatsapp channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [
            ["span", { text: "WhatsApp 1" }],
            [".badge", { text: "1" }],
        ],
    });
});

test("whatsapp are sorted by last activity time in the sidebar: most recent at the top", async () => {
    mockDate("2024-05-02 12:00:00");
    const pyEnv = await startServer();
    const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
        { name: "George" },
        { name: "Claude" },
    ]);
    pyEnv["discuss.channel"].create([
        {
            name: "WhatsApp 1",
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-01-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: partnerId1 }),
            ],
            channel_type: "whatsapp",
        },
        {
            name: "WhatsApp 2",
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-02-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: partnerId2 }),
            ],
            channel_type: "whatsapp",
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel-container)", {
        text: "WhatsApp 2",
    });
    await click(".o-mail-DiscussSidebarChannel", { text: "WhatsApp 1" });
    await insertText(".o-mail-Composer-input", "Blabla");
    await click(".o-mail-Composer-send:enabled");
    await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel-container)", {
        text: "WhatsApp 1",
    });
    await contains(":nth-child(2 of .o-mail-DiscussSidebarChannel-container)", {
        text: "WhatsApp 2",
    });
});

test("Whatsapp - Sidebar channel icons should have the partner's avatar", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "whatsapp",
    });
    const [partner] = pyEnv["res.partner"].search_read([["id", "=", partnerId]]);
    await start();
    await openDiscuss();
    await contains(
        `.o-mail-DiscussSidebar-item img[data-src='${getOrigin()}/web/image/res.partner/${partnerId}/avatar_128?unique=${
            deserializeDateTime(partner.write_date).ts
        }']`
    );
});
