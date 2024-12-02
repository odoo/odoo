import {
    click,
    defineMailModels,
    isInViewportOf,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Thread } from "@mail/core/common/thread";
import { describe, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("can highlight messages that are not yet loaded", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let middleMessageId;
    for (let i = 0; i < 200; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
        if (i === 100) {
            middleMessageId = messageId;
        }
    }
    await pyEnv["discuss.channel"].set_message_pin(channelId, middleMessageId, true);
    await start();
    await openDiscuss(channelId);
    await tick(); // Wait for the scroll to first unread to complete.
    await isInViewportOf(".o-mail-Message:contains(message 199)", ".o-mail-Thread");
    await click("a[data-oe-type='highlight']");
    await isInViewportOf(".o-mail-Message:contains(message 100)", ".o-mail-Thread");
});

test("can highlight message (slow ref registration)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let middleMessageId;
    for (let i = 0; i < 200; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
        if (i === 100) {
            middleMessageId = messageId;
        }
    }
    await pyEnv["discuss.channel"].set_message_pin(channelId, middleMessageId, true);
    let slowRegisterMessageRef = false;
    patchWithCleanup(Thread.prototype, {
        async registerMessageRef() {
            if (slowRegisterMessageRef) {
                // Ensure scroll is made even when messages are mounted later.
                await new Promise((res) => setTimeout(res, 250));
            }
            super.registerMessageRef(...arguments);
        },
    });
    await start();
    await openDiscuss(channelId);
    await tick(); // Wait for the scroll to first unread to complete.
    await isInViewportOf(".o-mail-Message:contains(message 199)", ".o-mail-Thread");
    slowRegisterMessageRef = true;
    await click("a[data-oe-type='highlight']");
    await isInViewportOf(".o-mail-Message:contains(message 100)", ".o-mail-Thread");
});
