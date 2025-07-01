import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";

import { Store } from "@mail/core/common/store_service";
import { LONG_TYPING, SHORT_TYPING } from "@mail/discuss/typing/common/composer_patch";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test('receive other member typing status "is typing"', async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from demo
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
});

test('receive other member typing status "is typing" then "no longer is typing"', async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
    // simulate receive typing notification from demo "is no longer typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
});

test('assume other member typing status becomes "no longer is typing" after long without any updated typing status', async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
    await advanceTime(Store.OTHER_LONG_TYPING);
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
});

test('other member typing status "is typing" refreshes of assuming no longer typing', async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
    // simulate receive typing notification from demo "is typing" again after long time.
    await advanceTime(LONG_TYPING);
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await advanceTime(LONG_TYPING);
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
    await advanceTime(Store.OTHER_LONG_TYPING - LONG_TYPING);
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
});

test('receive several other members typing status "is typing"', async () => {
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
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
            Command.create({ partner_id: partnerId_3 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    // simulate receive typing notification from other 10 (is typing)
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 10 is typing..." });
    // simulate receive typing notification from other 11 (is typing)
    withUser(userId_2, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 10 and Other 11 are typing..." });
    // simulate receive typing notification from other 12 (is typing)
    withUser(userId_3, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 10, Other 11 and more are typing..." });
    // simulate receive typing notification from other 10 (no longer is typing)
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 11 and Other 12 are typing..." });
    // simulate receive typing notification from other 10 (is typing again)
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Other 11, Other 12 and more are typing..." });
});

test("current partner notify is typing to other thread members", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "a");
    await assertSteps(["notify_typing:true"]);
    testEnded = true;
});

test("current partner notify is typing again to other members for long continuous typing", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await insertText(".o-mail-Composer-input", "a");
    await assertSteps(["notify_typing:true"]);
    // simulate current partner typing a character for a long time.
    const elapseTickTime = SHORT_TYPING / 2;
    for (let i = 0; i <= LONG_TYPING / elapseTickTime; i++) {
        await insertText(".o-mail-Composer-input", "a");
        await advanceTime(elapseTickTime);
    }
    await assertSteps(["notify_typing:true"]);
    testEnded = true;
});

test("current partner notify no longer is typing to thread members after 5 seconds inactivity", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/discuss/channel/notify_typing", (args) =>
        step(`notify_typing:${args.is_typing}`)
    );
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await insertText(".o-mail-Composer-input", "a");
    await assertSteps(["notify_typing:true"]);
    await advanceTime(SHORT_TYPING);
    await assertSteps(["notify_typing:false"]);
});

test("current partner is typing should not translate on textual typing status", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "a");
    await assertSteps(["notify_typing:true"]);
    await contains(".o-discuss-Typing");
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing...)" });
    testEnded = true;
});

test("chat: correspondent is typing", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({
        im_status: "online",
        name: "Demo",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel .o-mail-DiscussSidebarChannel-threadIcon");
    await contains(".fa-circle.text-success");
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing-icon[title='Demo is typing...']");
    // simulate receive typing notification from demo "no longer is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains(".fa-circle.text-success");
});

test("chat: correspondent is typing in chat window", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({
        im_status: "online",
        name: "Demo",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains("[title='Demo is typing...']", { count: 0 });
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains("[title='Demo is typing...']", { count: 2 }); // icon in header & text above composer
    // simulate receive typing notification from demo "no longer is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await contains("[title='Demo is typing...']", { count: 0 });
});

test("show typing in member list", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Other 10" });
    const partnerId = pyEnv["res.partner"].create({ name: "Other 10", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMember", { count: 2 });
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-ChannelMemberList [title='Other 10 is typing...']");
    withUser(serverState.userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(
        `.o-discuss-ChannelMemberList [title='${serverState.partnerName} is typing...']`
    );
});

test("switching to another channel triggers notify_typing to stop", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo" });
    const partnerId = pyEnv["res.partner"].create({
        im_status: "online",
        name: "Demo",
        user_ids: [userId],
    });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/discuss/channel/notify_typing", (args) =>
        step(`notify_typing:${args.is_typing}`)
    );
    await start();
    await openDiscuss(chatId);
    await insertText(".o-mail-Composer-input", "a");
    await assertSteps(["notify_typing:true"]);
    await click(".o-mail-DiscussSidebar-item", { text: "general" });
    await advanceTime(SHORT_TYPING / 2);
    await assertSteps(["notify_typing:false"]);
});
