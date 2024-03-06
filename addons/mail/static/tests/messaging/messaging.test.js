/** @odoo-module alias=@mail/../tests/messaging/messaging_tests default=false */

import { rpc } from "@web/core/network/rpc";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { openDiscuss, openFormView, start } from "@mail/../tests/helpers/test_utils";

import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";

QUnit.module("messaging");

QUnit.test("Receiving a new message out of discuss app should open a chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start({
        async mockRPC(route, args, originalRpc) {
            if (route === "/mail/action" && args.init_messaging) {
                const res = await originalRpc(...arguments);
                step(`/mail/action - ${JSON.stringify(args)}`);
                return res;
            }
        },
    });
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: pyEnv.currentUserId },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    // simulate receving new message
    pyEnv.withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
});

QUnit.test(
    "Receiving a new message in discuss app should open a chat window after leaving discuss app",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        await start({
            async mockRPC(route, args, originalRpc) {
                if (route === "/mail/action" && args.init_messaging) {
                    const res = await originalRpc(...arguments);
                    step(`/mail/action - ${JSON.stringify(args)}`);
                    return res;
                }
            },
        });
        await assertSteps([
            `/mail/action - ${JSON.stringify({
                init_messaging: {},
                failures: true,
                systray_get_activities: true,
                context: { lang: "en", tz: "taht", uid: pyEnv.currentUserId },
            })}`,
        ]);
        // send after init_messaging because bus subscription is done after init_messaging
        await openDiscuss();
        // simulate receiving new message
        pyEnv.withUser(userId, () =>
            rpc("/mail/message/post", {
                post_data: { body: "new message", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
    }
);

QUnit.test(
    "Posting a message in discuss app should not open a chat window after leaving discuss app",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        await start();
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
        await click(".o-mail-Composer-send:enabled");
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        // weak test, no guarantee that we waited long enough for the potential chat window to open
        await contains(".o-mail-ChatWindow", { count: 0, text: "Dumbledore" });
    }
);
