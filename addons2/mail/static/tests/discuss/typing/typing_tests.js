/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { LONG_TYPING, SHORT_TYPING } from "@mail/discuss/typing/common/composer_patch";
import { OTHER_LONG_TYPING } from "@mail/discuss/typing/common/typing_service";
import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("typing");

QUnit.test('receive other member typing status "is typing"', async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from demo
    pyEnv.withUser(userId, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
});

QUnit.test(
    'receive other member typing status "is typing" then "no longer is typing"',
    async () => {
        const pyEnv = await startServer();
        const userId = pyEnv["res.users"].create({ name: "Demo" });
        const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
        const channelId = pyEnv["discuss.channel"].create({
            name: "channel",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
        const { env, openDiscuss } = await start();
        await openDiscuss(channelId);
        await contains(".o-discuss-Typing");
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
        // simulate receive typing notification from demo "is typing"
        pyEnv.withUser(userId, () =>
            env.services.rpc("/discuss/channel/notify_typing", {
                channel_id: channelId,
                is_typing: true,
            })
        );
        await contains(".o-discuss-Typing", { text: "Demo is typing..." });
        // simulate receive typing notification from demo "is no longer typing"
        pyEnv.withUser(userId, () =>
            env.services.rpc("/discuss/channel/notify_typing", {
                channel_id: channelId,
                is_typing: false,
            })
        );
        await contains(".o-discuss-Typing");
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    }
);

QUnit.test(
    'assume other member typing status becomes "no longer is typing" after long without any updated typing status',
    async () => {
        const pyEnv = await startServer();
        const userId = pyEnv["res.users"].create({ name: "Demo" });
        const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
        const channelId = pyEnv["discuss.channel"].create({
            name: "channel",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
        const { advanceTime, env, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);
        await contains(".o-discuss-Typing");
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
        // simulate receive typing notification from demo "is typing"
        pyEnv.withUser(userId, () =>
            env.services.rpc("/discuss/channel/notify_typing", {
                channel_id: channelId,
                is_typing: true,
            })
        );
        await contains(".o-discuss-Typing", { text: "Demo is typing..." });
        advanceTime(OTHER_LONG_TYPING);
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    }
);

QUnit.test(
    'other member typing status "is typing" refreshes of assuming no longer typing',
    async () => {
        const pyEnv = await startServer();
        const userId = pyEnv["res.users"].create({ name: "Demo" });
        const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
        const channelId = pyEnv["discuss.channel"].create({
            name: "channel",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
        });
        const { advanceTime, env, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss(channelId);
        await contains(".o-discuss-Typing");
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
        // simulate receive typing notification from demo "is typing"
        pyEnv.withUser(userId, () =>
            env.services.rpc("/discuss/channel/notify_typing", {
                channel_id: channelId,
                is_typing: true,
            })
        );
        await contains(".o-discuss-Typing", { text: "Demo is typing..." });
        // simulate receive typing notification from demo "is typing" again after long time.
        await advanceTime(LONG_TYPING);
        await pyEnv.withUser(userId, () =>
            env.services.rpc("/discuss/channel/notify_typing", {
                channel_id: channelId,
                is_typing: true,
            })
        );
        await advanceTime(LONG_TYPING);
        await contains(".o-discuss-Typing", { text: "Demo is typing..." });
        advanceTime(OTHER_LONG_TYPING - LONG_TYPING);
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    }
);

QUnit.test('receive several other members typing status "is typing"', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2, userId_3] = pyEnv["res.users"].create([
        { name: "Other 10" },
        { name: "Other 11" },
        { name: "Other 12" },
    ]);
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Other 10", user_ids: [userId_1] },
        { name: "Other 11", user_ids: [userId_2] },
        { name: "Other 12", user_ids: [userId_3] },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
            Command.create({ partner_id: partnerId_3 }),
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from other 10 (is typing)
    pyEnv.withUser(userId_1, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 10 is typing..." });
    // simulate receive typing notification from other 11 (is typing)
    pyEnv.withUser(userId_2, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 10 and Other 11 are typing..." });
    // simulate receive typing notification from other 12 (is typing)
    pyEnv.withUser(userId_3, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 10, Other 11 and more are typing..." });
    // simulate receive typing notification from other 10 (no longer is typing)
    pyEnv.withUser(userId_1, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 11 and Other 12 are typing..." });
    // simulate receive typing notification from other 10 (is typing again)
    pyEnv.withUser(userId_1, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 11, Other 12 and more are typing..." });
});

QUnit.test("current partner notify is typing to other thread members", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/notify_typing") {
                assert.step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "a");
    assert.verifySteps(["notify_typing:true"]);
});

QUnit.test(
    "current partner notify is typing again to other members for long continuous typing",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "general" });
        const { advanceTime, openDiscuss } = await start({
            hasTimeControl: true,
            async mockRPC(route, args) {
                if (route === "/discuss/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "a");
        assert.verifySteps(["notify_typing:true"]);

        // simulate current partner typing a character for a long time.
        let totalTimeElapsed = 0;
        const elapseTickTime = SHORT_TYPING / 2;
        while (totalTimeElapsed < LONG_TYPING + SHORT_TYPING) {
            await insertText(".o-mail-Composer-input", "a");
            totalTimeElapsed += elapseTickTime;
            await advanceTime(elapseTickTime);
        }
        assert.verifySteps(["notify_typing:true"]);
    }
);

QUnit.test(
    "current partner notify no longer is typing to thread members after 5 seconds inactivity",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "general" });
        const { advanceTime, openDiscuss } = await start({
            hasTimeControl: true,
            async mockRPC(route, args) {
                if (route === "/discuss/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "a");
        assert.verifySteps(["notify_typing:true"]);

        await advanceTime(SHORT_TYPING);
        assert.verifySteps(["notify_typing:false"]);
    }
);

QUnit.test(
    "current partner is typing should not translate on textual typing status",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "general" });
        const { openDiscuss } = await start({
            hasTimeControl: true,
            async mockRPC(route, args) {
                if (route === "/discuss/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "a");
        assert.verifySteps(["notify_typing:true"]);
        await contains(".o-discuss-Typing");
        await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    }
);

QUnit.test("chat: correspondent is typing", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({
        im_status: "online",
        name: "Demo",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel .o-mail-DiscussSidebarChannel-threadIcon");
    await contains(".fa-circle.text-success");
    // simulate receive typing notification from demo "is typing"
    pyEnv.withUser(userId, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing-icon[title='Demo is typing...']");
    // simulate receive typing notification from demo "no longer is typing"
    pyEnv.withUser(userId, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains(".fa-circle.text-success");
});

QUnit.test("chat: correspondent is typing in chat window", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({
        im_status: "online",
        name: "Demo",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains("[title='Demo is typing...']", { count: 0 });
    // simulate receive typing notification from demo "is typing"
    pyEnv.withUser(userId, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains("[title='Demo is typing...']", { count: 2 }); // icon in header & text above composer
    // simulate receive typing notification from demo "no longer is typing"
    pyEnv.withUser(userId, () =>
        env.services.rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains("[title='Demo is typing...']", { count: 0 });
});
