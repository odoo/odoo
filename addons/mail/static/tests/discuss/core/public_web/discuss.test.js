import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    Command,
    mockService,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("open channel in discuss from push notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-DiscussContent-threadName[title='Inbox']");
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId } },
        })
    );
    await contains(".o-mail-DiscussContent-threadName[title='General']");
});

test("notify message to user as non member", async () => {
    patchWithCleanup(window, {
        Notification: class Notification {
            static get permission() {
                return "granted";
            }
            constructor() {
                expect.step("push notification");
            }
            addEventListener() {}
        },
    });
    mockService("multi_tab", { isOnMainTab: () => true });
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
    });
    await start();
    await Promise.all([openDiscuss(channelId), waitUntilSubscribe(`discuss.channel_${channelId}`)]);
    await withUser(johnUser, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message:has(:text('Hello!'))");
    expect.verifySteps(["push notification"]);
});

test("show correspondent local time in DM header when timezones differ", async () => {
    mockDate("2026-01-01 12:00:00");
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { tz: "Europe/Brussels" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", tz: "Asia/Kolkata" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header:has(:text('17:30 local time'))");
});
