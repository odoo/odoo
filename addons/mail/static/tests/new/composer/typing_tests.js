/** @odoo-module **/

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import {
    afterNextRender,
    insertText,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { LONG_TYPING, SHORT_TYPING } from "@mail/new/composer/composer";
import { OTHER_LONG_TYPING } from "@mail/new/core/messaging_service";

let target;
QUnit.module("typing", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test('receive other member typing status "is typing"', async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["mail.channel"].create({
        name: "channel",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");

    // simulate receive typing notification from demo
    await afterNextRender(() =>
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId },
            is_typing: true,
        })
    );
    assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "Demo is typing...");
});

QUnit.test(
    'receive other member typing status "is typing" then "no longer is typing"',
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const channelId = pyEnv["mail.channel"].create({
            name: "channel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const { env, openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");

        // simulate receive typing notification from demo "is typing"
        await afterNextRender(() =>
            env.services.rpc("/mail/channel/notify_typing", {
                channel_id: channelId,
                context: { mockedPartnerId: partnerId },
                is_typing: true,
            })
        );
        assert.strictEqual(
            $(target).find(".o-mail-composer-is-typing").text(),
            "Demo is typing..."
        );

        // simulate receive typing notification from demo "is no longer typing"
        await afterNextRender(() =>
            env.services.rpc("/mail/channel/notify_typing", {
                channel_id: channelId,
                context: { mockedPartnerId: partnerId },
                is_typing: false,
            })
        );
        assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");
    }
);

QUnit.test(
    'assume other member typing status becomes "no longer is typing" after long without any updated typing status',
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const channelId = pyEnv["mail.channel"].create({
            name: "channel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const { advanceTime, env, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);

        assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");

        // simulate receive typing notification from demo "is typing"
        await afterNextRender(() =>
            env.services.rpc("/mail/channel/notify_typing", {
                channel_id: channelId,
                context: { mockedPartnerId: partnerId },
                is_typing: true,
            })
        );
        assert.strictEqual(
            $(target).find(".o-mail-composer-is-typing").text(),
            "Demo is typing..."
        );

        await afterNextRender(() => advanceTime(OTHER_LONG_TYPING));
        assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");
    }
);

QUnit.test(
    'other member typing status "is typing" refreshes of assuming no longer typing',
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const channelId = pyEnv["mail.channel"].create({
            name: "channel",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
        });
        const { advanceTime, env, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);
        assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");

        // simulate receive typing notification from demo "is typing"
        await afterNextRender(() =>
            env.services.rpc("/mail/channel/notify_typing", {
                channel_id: channelId,
                context: {
                    mockedPartnerId: partnerId,
                },
                is_typing: true,
            })
        );
        assert.strictEqual(
            $(target).find(".o-mail-composer-is-typing").text(),
            "Demo is typing..."
        );

        // simulate receive typing notification from demo "is typing" again after long time.
        await advanceTime(LONG_TYPING);
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId },
            is_typing: true,
        });
        await nextTick();
        await advanceTime(LONG_TYPING);
        await nextAnimationFrame();
        assert.strictEqual(
            $(target).find(".o-mail-composer-is-typing").text(),
            "Demo is typing..."
        );
        await afterNextRender(() => advanceTime(OTHER_LONG_TYPING - LONG_TYPING));
        assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");
    }
);

QUnit.test('receive several other members typing status "is typing"', async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Other 10" },
        { name: "Other 11" },
        { name: "Other 12" },
    ]);
    const channelId = pyEnv["mail.channel"].create({
        name: "channel",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId_1 }],
            [0, 0, { partner_id: partnerId_2 }],
            [0, 0, { partner_id: partnerId_3 }],
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.strictEqual($(target).find(".o-mail-composer-is-typing").text(), "");

    // simulate receive typing notification from other 10 (is typing)
    await afterNextRender(() =>
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId_1 },
            is_typing: true,
        })
    );
    assert.strictEqual(
        $(target).find(".o-mail-composer-is-typing").text(),
        "Other 10 is typing..."
    );

    // simulate receive typing notification from other 11 (is typing)
    await afterNextRender(() =>
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId_2 },
            is_typing: true,
        })
    );
    assert.strictEqual(
        $(target).find(".o-mail-composer-is-typing").text(),
        "Other 10 and Other 11 are typing...",
        "Should display that members 'Other 10' and 'Other 11' are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other 12 (is typing)
    await afterNextRender(() =>
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId_3 },
            is_typing: true,
        })
    );
    assert.strictEqual(
        $(target).find(".o-mail-composer-is-typing").text(),
        "Other 10, Other 11 and more are typing...",
        "Should display that members 'Other 10', 'Other 11' and more (at least 1 extra member) are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other 10 (no longer is typing)
    await afterNextRender(() =>
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId_1 },
            is_typing: false,
        })
    );
    assert.strictEqual(
        $(target).find(".o-mail-composer-is-typing").text(),
        "Other 11 and Other 12 are typing...",
        "Should display that members 'Other 11' and 'Other 12' are typing ('Other 10' stopped typing)"
    );

    // simulate receive typing notification from other 10 (is typing again)
    await afterNextRender(() =>
        env.services.rpc("/mail/channel/notify_typing", {
            channel_id: channelId,
            context: { mockedPartnerId: partnerId_1 },
            is_typing: true,
        })
    );
    assert.strictEqual(
        $(target).find(".o-mail-composer-is-typing").text(),
        "Other 11, Other 12 and more are typing...",
        "Should display that members 'Other 11' and 'Other 12' and more (at least 1 extra member) are typing (order by longer typer, 'Other 10' just recently restarted typing)"
    );
});

QUnit.test("current partner notify is typing to other thread members", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/channel/notify_typing") {
                assert.step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-composer-textarea", "a");
    assert.verifySteps(["notify_typing:true"]);
});

QUnit.test(
    "current partner notify is typing again to other members for long continuous typing",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "general" });
        const { advanceTime, openDiscuss } = await start({
            hasTimeControl: true,
            async mockRPC(route, args) {
                if (route === "/mail/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-composer-textarea", "a");
        assert.verifySteps(["notify_typing:true"]);

        // simulate current partner typing a character for a long time.
        let totalTimeElapsed = 0;
        const elapseTickTime = SHORT_TYPING / 2;
        while (totalTimeElapsed < LONG_TYPING + SHORT_TYPING) {
            await insertText(".o-mail-composer-textarea", "a");
            totalTimeElapsed += elapseTickTime;
            await advanceTime(elapseTickTime);
        }
        assert.verifySteps(["notify_typing:true"]);
    }
);

QUnit.test(
    "current partner notify no longer is typing to thread members after 5 seconds inactivity",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "general" });
        const { advanceTime, openDiscuss } = await start({
            hasTimeControl: true,
            async mockRPC(route, args) {
                if (route === "/mail/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-composer-textarea", "a");
        assert.verifySteps(["notify_typing:true"]);

        await advanceTime(SHORT_TYPING);
        assert.verifySteps(["notify_typing:false"]);
    }
);

QUnit.test(
    "current partner is typing should not translate on textual typing status",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "general" });
        const { openDiscuss } = await start({
            hasTimeControl: true,
            async mockRPC(route, args) {
                if (route === "/mail/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-composer-textarea", "a");
        assert.verifySteps(["notify_typing:true"]);

        await nextAnimationFrame();
        assert.strictEqual($(target).find(".o-mail-composer-is-typing-space-holder").text(), "");
    }
);
