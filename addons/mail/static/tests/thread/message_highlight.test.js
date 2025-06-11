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
import { advanceTime, Deferred, tick, waitFor } from "@odoo/hoot-dom";
import { disableAnimations } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("can highlight messages that are not yet loaded", async () => {
    disableAnimations();
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
    disableAnimations();
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
    let slowRegisterMessageDef;
    patchWithCleanup(Thread.prototype, {
        async registerMessageRef(...args) {
            // Ensure scroll is made even when messages are mounted later.
            await slowRegisterMessageDef;
            return super.registerMessageRef(...args);
        },
    });
    await start();
    await openDiscuss(channelId);
    await tick(); // Wait for the scroll to first unread to complete.
    await isInViewportOf(".o-mail-Message:contains(message 199)", ".o-mail-Thread");
    slowRegisterMessageDef = new Deferred();
    await click("a[data-oe-type='highlight']");
    await advanceTime(1000);
    slowRegisterMessageDef.resolve();
    await isInViewportOf(".o-mail-Message:contains(message 100)", ".o-mail-Thread");
});

test("highlight scrolls to beginning of long message", async () => {
    disableAnimations();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const [messageId1] = pyEnv["mail.message"].create([
        {
            body: `long message `.repeat(500),
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: `short message`,
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await pyEnv["discuss.channel"].set_message_pin(channelId, messageId1, true);
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:contains('short message')");
    await isInViewportOf(".o-mail-Message:contains('short message')", ".o-mail-Thread");
    await click("a[data-oe-type='highlight']");
    await advanceTime(1000);
    await isInViewportOf(".o-mail-Message:contains('long message')", ".o-mail-Thread");
    await isInViewportOf(
        ".o-mail-Message:contains('long message') .o-mail-Message-avatar", // avatar is at beginning of message
        ".o-mail-Thread"
    );
});
