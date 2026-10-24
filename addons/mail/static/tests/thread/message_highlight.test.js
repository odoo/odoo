import {
    contains as mailContains,
    defineMailModels,
    isInViewportOf,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { HIGHLIGHT_DURATION } from "@mail/core/common/message_highlight_plugin";
import { UseForwardRefsToParent } from "@mail/utils/common/hooks";
import { SCROLL_IDLE_DELAY, ScrollManager } from "@mail/utils/common/scroll";
import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, tick, waitFor, waitForNone } from "@odoo/hoot-dom";
import { disableAnimations } from "@odoo/hoot-mock";
import { router, routerBus } from "@web/core/browser/router";
import { range } from "@web/core/utils/numbers";
import { contains, mountWebClient } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

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
    await contains("a[data-oe-type='highlight']:count(1)").click();
    await isInViewportOf(".o-mail-Message:contains(message 100)", ".o-mail-Thread");
});

test("highlight scroll is not stopped by the scrollend of a previous scroll", async () => {
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
    patch(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView(options);
            if (options?.behavior === "smooth") {
                // Simulate the late scroll and scrollend of the previous scroll.
                const threadEl = this.closest(".o-mail-Thread");
                threadEl.dispatchEvent(new Event("scroll"));
                threadEl.dispatchEvent(new Event("scrollend"));
            }
        },
    });
    await start();
    await openDiscuss(channelId);
    await isInViewportOf(".o-mail-Message:contains(message 199)", ".o-mail-Thread");
    await contains("a[data-oe-type='highlight']:count(1)").click();
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
    const { promise: refRegistered, resolve: resolveRefRegistration } = Promise.withResolvers();
    patch(UseForwardRefsToParent.prototype, {
        async registerRef(...args) {
            // Ensure scroll is made even when messages are mounted later.
            await refRegistered;
            return super.registerRef(...args);
        },
    });
    await start();
    await openDiscuss(channelId);
    await tick(); // Wait for the scroll to first unread to complete.
    await isInViewportOf(".o-mail-Message:contains(message 199)", ".o-mail-Thread");
    await contains("a[data-oe-type='highlight']:count(1)").click();
    await advanceTime(HIGHLIGHT_DURATION / 2);
    resolveRefRegistration();
    await isInViewportOf(".o-mail-Message:contains(message 100)", ".o-mail-Thread");
});

test("no scroll to highlighted message rendered after the highlight is cleared", async () => {
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
    const { promise: refRegistered, resolve: resolveRefRegistration } = Promise.withResolvers();
    patch(UseForwardRefsToParent.prototype, {
        async registerRef(...args) {
            await refRegistered;
            return super.registerRef(...args);
        },
    });
    patch(ScrollManager.prototype, {
        revealItem() {
            expect.step("reveal");
            return super.revealItem(...arguments);
        },
    });
    await start();
    await openDiscuss(channelId);
    await tick(); // Wait for the scroll to first unread to complete.
    await isInViewportOf(".o-mail-Message:contains(message 199)", ".o-mail-Thread");
    await contains("a[data-oe-type='highlight']:count(1)").click();
    await waitFor(".o-mail-Message.o-highlighted:contains(message 100)");
    await advanceTime(HIGHLIGHT_DURATION);
    await waitForNone(".o-mail-Message.o-highlighted");
    resolveRefRegistration();
    await advanceTime(SCROLL_IDLE_DELAY);
    await animationFrame();
    expect.verifySteps([]);
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
    await contains("a[data-oe-type='highlight']:count(1)").click();
    await advanceTime(SCROLL_IDLE_DELAY);
    await isInViewportOf(".o-mail-Message:contains('long message')", ".o-mail-Thread");
    await isInViewportOf(
        ".o-mail-Message:contains('long message') .o-mail-Message-avatar", // avatar is at beginning of message
        ".o-mail-Thread"
    );
});

test("Chatter jumps when navigating to a specific message link", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const messageIds = range(0, 31).map((i) =>
        pyEnv["mail.message"].create({
            body: `message ${i}`,
            model: "res.partner",
            res_id: partnerId,
        })
    );
    await mountWebClient();
    router.pushState(
        router.urlToState(
            new URL(
                `${window.location.origin}/odoo/res.partner/${partnerId}?highlight_message_id=${messageIds[0]}`
            )
        ),
        { sync: true }
    );
    routerBus.trigger("ROUTE_CHANGE");
    await mailContains(".o-mail-Message.o-highlighted .o-mail-Message-content", {
        text: "message 0",
    });
});
