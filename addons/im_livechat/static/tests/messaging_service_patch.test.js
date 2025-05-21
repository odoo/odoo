import {
    contains,
    listenStoreFetch,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("push notifications are Odoo toaster on Android", async () => {
    // Notifications without ServiceWorker in Chrome Android no longer work.
    // This simulates Android Notification behavior by throwing a
    // ServiceWorkerRegistration error as a fallback.
    patchWithCleanup(window, {
        Notification: class Notification {
            static get permission() {
                return "granted";
            }
            constructor() {
                throw new Error("ServiceWorkerRegistration error");
            }
        },
    });
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    // send after init_messaging because bus subscription is done after init_messaging
    await withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello world!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_model: "discuss.channel",
            thread_id: channelId,
        })
    );
    await contains(".o_notification:has(.o_notification_bar.bg-info)", {
        text: "Visitor. Hello world!",
    });
});
