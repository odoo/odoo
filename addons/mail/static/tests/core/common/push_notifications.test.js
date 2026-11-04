import {
    contains,
    defineMailModels,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    getService,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

defineMailModels();
describe.current.tags("desktop");

for (const subscribed of [false, true]) {
    test(`record push: inbox bus notification with push subscription ${subscribed}`, async () => {
        const pyEnv = await startServer();
        pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        await start();
        await openDiscuss();
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
        const recipientId = serverState.partnerId;
        await withUser(userId, () =>
            rpc("/mail/message/post", {
                thread_model: "res.partner",
                thread_id: partnerId,
                post_data: {
                    body: "Hello from the chatter",
                    message_type: "comment",
                    partner_ids: [recipientId],
                },
            })
        );
        await contains(".o-mail-DiscussSidebar-item:has(.badge)", { text: "Inbox" });
        expect(getService("mail.store").inbox.counter).toBe(1);
        await expect.waitForSteps(
            subscribed ? ["get subscription"] : ["get subscription", "local notification"]
        );
    });
}

for (const preference of ["inbox", "email"]) {
    for (const isFocused of [false, true]) {
        test(`record push: ${preference} preference with focused window ${isFocused}`, async () => {
            const pyEnv = await startServer();
            pyEnv["res.users"].write(serverState.userId, { notification_type: preference });
            const [partnerId, otherPartnerId] = pyEnv["res.partner"].create([
                { name: "Displayed contact" },
                { name: "Other contact" },
            ]);
            await start();
            await openFormView("res.partner", partnerId);
            await contains(".o-mail-Chatter");
            patchWithCleanup(parent.document, { hasFocus: () => isFocused });
            patchWithCleanup(browser.navigator.serviceWorker, {
                controller: {
                    postMessage(message) {
                        expect(message.type).toBe("notification-display-response");
                        expect.step(message.payload.correlationId);
                    },
                },
            });
            for (const [resId, correlationId] of [
                [partnerId, "displayed record"],
                [otherPartnerId, "other record"],
            ]) {
                browser.navigator.serviceWorker.dispatchEvent(
                    new MessageEvent("message", {
                        data: {
                            type: "notification-display-request",
                            payload: { model: "res.partner", res_id: resId, correlationId },
                        },
                    })
                );
            }
            expect.verifySteps([]);
        });
    }
}

for (const isFocused of [false, true]) {
    test(`channel push: focused window ${isFocused}`, async () => {
        const pyEnv = await startServer();
        const [channelId, otherChannelId] = pyEnv["discuss.channel"].create([
            { name: "Displayed channel" },
            { name: "Other channel" },
        ]);
        await start();
        await openDiscuss(channelId);
        await contains(".o-mail-DiscussContent-threadName[title='Displayed channel']");
        patchWithCleanup(parent.document, { hasFocus: () => isFocused });
        patchWithCleanup(browser.navigator.serviceWorker, {
            controller: {
                postMessage(message) {
                    expect(message.type).toBe("notification-display-response");
                    expect.step(message.payload.correlationId);
                },
            },
        });
        for (const [resId, correlationId] of [
            [channelId, "displayed channel"],
            [otherChannelId, "other channel"],
        ]) {
            browser.navigator.serviceWorker.dispatchEvent(
                new MessageEvent("message", {
                    data: {
                        type: "notification-display-request",
                        payload: { model: "discuss.channel", res_id: resId, correlationId },
                    },
                })
            );
        }
        expect.verifySteps(isFocused ? ["displayed channel"] : []);
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
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Message-body:text('Unread message')");
    await openDiscuss("mail.box_history");
    await contains(".o-mail-Message-body:text('Read message')");
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
