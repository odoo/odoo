import { waitForChannels } from "@bus/../tests/bus_test_helpers";

import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import {
    click,
    contains,
    openMessagingMenu,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";

import { Command, mockService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("live chat tab displays kanban action when empty", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    mockService("action", { doAction: (action) => expect.step(action) });
    await start();
    await openMessagingMenu("livechat");
    await contains(".o-mail-MessagingMenuEmpty .fw-bold:text('No Livechat Session!')");
    await contains(
        ".o-mail-MessagingMenuEmpty :text('Engage with visitors to convert leads or offer services.')"
    );
    await click(".o-mail-MessagingMenuEmpty button:text(Connect)");
    await expect.waitForSteps(["im_livechat.im_livechat_channel_action"]);
});

test("live chat tab display live chat channels", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    await start();
    await openMessagingMenu("livechat");
    await contains(".o-mail-NotificationItem", { text: "Visitor 11" });
});

test("live chat tab has a need help filter", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const [guest1, guest2] = pyEnv["mail.guest"].create([
        { name: "Visitor #1" },
        { name: "Visitor #2" },
    ]);
    pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    livechat_member_type: "agent",
                }),
                Command.create({ guest_id: guest1, livechat_member_type: "visitor" }),
            ],
            channel_type: "livechat",
            livechat_status: "need_help",
        },
        {
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    livechat_member_type: "agent",
                }),
                Command.create({ guest_id: guest2, livechat_member_type: "visitor" }),
            ],
            channel_type: "livechat",
            livechat_status: "in_progress",
        },
    ]);
    await start();
    await openMessagingMenu("livechat");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await click("button:text('Help needed')");
    await waitForChannels(["im_livechat.looking_for_help"]);
    await contains(".o-mail-NotificationItem", { count: 1 });
    await contains(".o-mail-NotificationItem", { text: "Visitor #1" });
    await contains(".o-mail-NotificationItem", { count: 0, text: "Visitor #2" });
});
