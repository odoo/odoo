import {
    click,
    contains,
    defineMailModels,
    MENU_ACTIVE_IDS,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Store } from "@mail/../tests/mock_server/store";
import { describe, expect, test } from "@odoo/hoot";
import { getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";

defineMailModels();
describe.current.tags("desktop");

for (const subscribed of [false, true]) {
    test(`record push: inbox bus notification with push subscription ${subscribed}`, async () => {
        const pyEnv = await startServer();
        pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        await start();
        await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
        patchWithCleanup(browser.navigator.serviceWorker, {
            async getRegistration() {
                return {
                    pushManager: {
                        async getSubscription() {
                            expect.step("get subscription");
                            return subscribed ? {} : null;
                        },
                    },
                };
            },
        });
        patchWithCleanup(getService("mail.out_of_focus"), {
            sendNotification() {
                expect.step("local notification");
            },
        });
        const messageId = pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "Hello from the chatter",
            message_type: "comment",
            model: "res.partner",
            needaction: true,
            res_id: partnerId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        });
        const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
        pyEnv["bus.bus"]._sendone(partner, "mail.message/notification", {
            message_id: messageId,
            store_data: new Store()
                .add(pyEnv["mail.message"].browse(messageId), "_store_message_fields", {
                    fields_params: { inbox_fields: true },
                })
                .as_dict(),
        });
        await contains(".o-mail-MessagingMenu-tab:has(:text('Notifications')):has(.badge:text(1))");
        await expect.waitForSteps(
            subscribed ? ["get subscription"] : ["get subscription", "local notification"]
        );
    });
}

test("record push: message already read in inbox", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const [readMessageId, unreadMessageId] = pyEnv["mail.message"].create([
        { body: "Read message", message_type: "comment", model: "res.partner", res_id: partnerId },
        {
            body: "Unread message",
            message_type: "comment",
            model: "res.partner",
            needaction: true,
            res_id: partnerId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: readMessageId,
            notification_type: "inbox",
            is_read: true,
            res_partner_id: serverState.partnerId,
        },
        {
            mail_message_id: unreadMessageId,
            notification_type: "inbox",
            res_partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await contains(".o-mail-MessagingMenuItem:has(:text('You: Unread message'))");
    await click("button:text('All')");
    await contains(".o-mail-MessagingMenuItem:has(:text('You: Read message'))");
    patchWithCleanup(parent.document, { hasFocus: () => false });
    patchWithCleanup(browser.navigator.serviceWorker, {
        controller: {
            postMessage(message) {
                expect.step(message.payload.correlationId);
            },
        },
    });
    for (const [messageId, correlationId] of [
        [readMessageId, "read message"],
        [unreadMessageId, "unread message"],
    ]) {
        browser.navigator.serviceWorker.dispatchEvent(
            new MessageEvent("message", {
                data: {
                    type: "notification-display-request",
                    payload: {
                        model: "res.partner",
                        res_id: partnerId,
                        message_id: messageId,
                        correlationId,
                    },
                },
            })
        );
    }
    expect.verifySteps(["read message"]);
});
