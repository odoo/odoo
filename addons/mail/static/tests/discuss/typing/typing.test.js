import {
    actionPanel,
    click,
    contains,
    defineMailModels,
    hover,
    insertText,
    onRpcBefore,
    openDiscuss,
    openMessagingMenu,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { htmlInsertText } from "@mail/../tests/mail_test_helpers_html";
import { animationFrame, describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { advanceTime, mockDate } from "@odoo/hoot-mock";
import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import { Store } from "@mail/core/common/store_plugin";
import { LONG_TYPING, SHORT_TYPING } from "@mail/discuss/typing/common/composer_patch";
import { rpc } from "@web/core/network/rpc";
import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";

describe.current.tags("desktop");
defineMailModels();

test('[text composer] receive other member typing status "is typing"', async () => {
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
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    // simulate receive typing notification from demo
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
});

test.tags("html composer");
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
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
});

test('[text composer] receive other member typing status "is typing" then "no longer is typing"', async () => {
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
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    // simulate receive typing notification from demo "is no longer typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
});

test.tags("html composer");
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
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
});

test('[text composer] assume other member typing status becomes "no longer is typing" after long without any updated typing status', async () => {
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
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await advanceTime(Store.OTHER_LONG_TYPING);
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
});

test.tags("html composer");
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
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await advanceTime(Store.OTHER_LONG_TYPING);
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
});

test('"is typing" timeout should work even when 2 notify_typing happen at the exact same time', async () => {
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
    mockDate("2024-01-01 12:00:00");
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "Demo is typing..." });
    await advanceTime(Store.OTHER_LONG_TYPING);
    await contains(".o-discuss-Typing", { count: 0, text: "Demo is typing..." });
});

test('[text composer] other member typing status "is typing" refreshes of assuming no longer typing', async () => {
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
    patch(ChannelMember.prototype, {
        registerTypingTimeout(...args) {
            expect.step("register_typing_timeout");
            super.registerTypingTimeout(...args);
        },
    });
    onRpcBefore("/discuss/channel/notify_typing", () => {
        expect.step("notify_typing");
    });
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await expect.waitForSteps(["notify_typing", "register_typing_timeout"]);
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    // simulate receive typing notification from demo "is typing" again after long time.
    await advanceTime(LONG_TYPING);
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await expect.waitForSteps([
        "register_typing_timeout",
        "notify_typing",
        "register_typing_timeout",
    ]);
    await advanceTime(LONG_TYPING);
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await advanceTime(Store.OTHER_LONG_TYPING - LONG_TYPING);
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
});

test.tags("html composer");
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
    patch(ChannelMember.prototype, {
        registerTypingTimeout(...args) {
            expect.step("register_typing_timeout");
            super.registerTypingTimeout(...args);
        },
    });
    onRpcBefore("/discuss/channel/notify_typing", () => {
        expect.step("notify_typing");
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await expect.waitForSteps(["notify_typing", "register_typing_timeout"]);
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await advanceTime(LONG_TYPING);
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await expect.waitForSteps([
        "register_typing_timeout",
        "notify_typing",
        "register_typing_timeout",
    ]);
    await advanceTime(LONG_TYPING);
    await waitFor(".o-discuss-Typing:text('Demo is typing...'):count(1)");
    await advanceTime(Store.OTHER_LONG_TYPING - LONG_TYPING);
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
});

test('[text composer] receive several other members typing status "is typing"', async () => {
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
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    // simulate receive typing notification from other 10 (is typing)
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 10 is typing...'):count(1)");
    // simulate receive typing notification from other 11 (is typing)
    withUser(userId_2, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 10 and Other 11 are typing...'):count(1)");
    // simulate receive typing notification from other 12 (is typing)
    withUser(userId_3, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 10, Other 11 and more are typing...'):count(1)");
    // simulate receive typing notification from other 10 (no longer is typing)
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 11 and Other 12 are typing...'):count(1)");
    // simulate receive typing notification from other 10 (is typing again)
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 11, Other 12 and more are typing...'):count(1)");
});

test.tags("html composer");
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
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 10 is typing...'):count(1)");
    withUser(userId_2, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 10 and Other 11 are typing...'):count(1)");
    withUser(userId_3, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 10, Other 11 and more are typing...'):count(1)");
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 11 and Other 12 are typing...'):count(1)");
    withUser(userId_1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing:text('Other 11, Other 12 and more are typing...'):count(1)");
});

test("[text composer] current partner notify is typing to other thread members", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "a");
    await expect.waitForSteps(["notify_typing:true"]);
    testEnded = true;
});

test.tags("html composer");
test("current partner notify is typing to other thread members", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:count(1)");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "a");
    await expect.waitForSteps(["notify_typing:true"]);
    testEnded = true;
});

test("[text composer] current partner notify is typing again to other members for long continuous typing", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await insertText(".o-mail-Composer-input", "a");
    await expect.waitForSteps(["notify_typing:true"]);
    // simulate current partner typing a character for a long time.
    const elapseTickTime = SHORT_TYPING / 2;
    for (let i = 0; i <= LONG_TYPING / elapseTickTime; i++) {
        await insertText(".o-mail-Composer-input", "a");
        await advanceTime(elapseTickTime);
    }
    await expect.waitForSteps(["notify_typing:true"]);
    testEnded = true;
});

test.tags("html composer");
test("current partner notify is typing again to other members for long continuous typing", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:count(1)");
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "a");
    await expect.waitForSteps(["notify_typing:true"]);
    const elapseTickTime = SHORT_TYPING / 2;
    for (let i = 0; i <= LONG_TYPING / elapseTickTime; i++) {
        await htmlInsertText(editor, "a");
        await advanceTime(elapseTickTime);
    }
    await expect.waitForSteps(["notify_typing:true"]);
    testEnded = true;
});

test("[text composer] current partner notify no longer is typing to thread members after 5 seconds inactivity", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/discuss/channel/notify_typing", (args) =>
        expect.step(`notify_typing:${args.is_typing}`)
    );
    await start();
    await openDiscuss(channelId);
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await insertText(".o-mail-Composer-input", "a");
    await expect.waitForSteps(["notify_typing:true"]);
    await advanceTime(SHORT_TYPING);
    await expect.waitForSteps(["notify_typing:false"]);
});

test.tags("html composer");
test("current partner notify no longer is typing to thread members after 5 seconds inactivity", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/discuss/channel/notify_typing", (args) =>
        expect.step(`notify_typing:${args.is_typing}`)
    );
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:count(1)");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "a");
    await expect.waitForSteps(["notify_typing:true"]);
    await advanceTime(SHORT_TYPING);
    await expect.waitForSteps(["notify_typing:false"]);
});

test("[text composer] current partner is typing should not translate on textual typing status", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "a");
    await expect.waitForSteps(["notify_typing:true"]);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    testEnded = true;
});

test.tags("html composer");
test("current partner is typing should not translate on textual typing status", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let testEnded = false;
    onRpcBefore("/discuss/channel/notify_typing", (args) => {
        if (!testEnded) {
            expect.step(`notify_typing:${args.is_typing}`);
        }
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:count(1)");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "a");
    await expect.waitForSteps(["notify_typing:true"]);
    await waitFor(".o-discuss-Typing:count(1)");
    await waitForNone(".o-discuss-Typing:text('Demo is typing...')");
    testEnded = true;
});

test("[text composer] chat: correspondent is typing", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await waitFor(
        ".o-mail-MessagingMenuItem .o-mail-ThreadIcon[data-icon='circle'].text-success:count(1)"
    );
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing-icon[title='Demo is typing...']:count(1)");
    // simulate receive typing notification from demo "no longer is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitFor(
        ".o-mail-MessagingMenuItem .o-mail-ThreadIcon[data-icon='circle'].text-success:count(1)"
    );
});

test("Do not show typing indicator when channel is muted", async () => {
    const pyEnv = await startServer();
    const [userId1, userId2] = pyEnv["res.users"].create([
        { name: "Demo", im_status: "online" },
        { name: "Demo2", im_status: "online" },
    ]);
    const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
        { name: "Demo", user_ids: [userId1] },
        { name: "Demo2", user_ids: [userId2] },
    ]);
    const [channelId1, channelId2] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId2 }),
            ],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "some message",
            model: "discuss.channel",
            res_id: channelId1,
        },
        {
            author_id: serverState.partnerId,
            body: "some message",
            model: "discuss.channel",
            res_id: channelId1,
        },
    ]);
    await start();
    await openDiscuss(channelId1);
    await waitFor(".o-mail-Message:count(2)");
    await rpc("/discuss/settings/mute", { minutes: -1, channel_id: channelId2 });
    withUser(userId2, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId2,
            is_typing: true,
        })
    );
    withUser(userId1, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId1,
            is_typing: true,
        })
    );
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text('Demo')) .o-discuss-Typing-icon[title='Demo is typing...']:count(1)"
    );
    await waitForNone(
        ".o-mail-MessagingMenuItem:has(:text('Demo2')) .o-discuss-Typing-icon[title='Demo is typing...']"
    );
});

test.tags("html composer");
test("chat: correspondent is typing", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss();
    await waitFor(
        ".o-mail-MessagingMenuItem .o-mail-ThreadIcon[data-icon='circle'].text-success:count(1)"
    );
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(".o-discuss-Typing-icon[title='Demo is typing...']:count(1)");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitFor(
        ".o-mail-MessagingMenuItem .o-mail-ThreadIcon[data-icon='circle'].text-success:count(1)"
    );
});

test("[text composer] chat: correspondent is typing in chat window", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openMessagingMenu();
    await click(".o-mail-NotificationItem");
    await waitForNone("[title='Demo is typing...']");
    // simulate receive typing notification from demo "is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor("[title='Demo is typing...']:count(1)");
    // simulate receive typing notification from demo "no longer is typing"
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitForNone("[title='Demo is typing...']");
});

test.tags("html composer");
test("chat: correspondent is typing in chat window", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openMessagingMenu();
    await click(".o-mail-NotificationItem");
    await waitForNone("[title='Demo is typing...']");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor("[title='Demo is typing...']:count(1)");
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: false,
        })
    );
    await waitForNone("[title='Demo is typing...']");
});

test("[text composer] show typing in member list", async () => {
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
    await waitFor(".o-discuss-ChannelMember:count(2)");
    // simulate other user typing
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(`${actionPanel("Members")} [title='Other 10 is typing...']:count(1)`);
    await insertText(".o-mail-Composer-input", "HelloWorld!");
    await waitFor(
        `${actionPanel("Members")} [title='${serverState.partnerName} is typing...']:count(1)`
    );
    await click(".o-mail-Composer button:enabled[aria-label='Send']");
    await waitForNone(
        `${actionPanel("Members")} [title='${serverState.partnerName} is typing...']`
    );
    await advanceTime(Store.OTHER_LONG_TYPING);
    await waitForNone(`${actionPanel("Members")} [title='Other 10 is typing...']`);
    // check editing doesn't trigger is typing
    await waitFor(".o-mail-Message-content:has(:text('HelloWorld!')):count(1)");
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:text('Edit')");
    await insertText(".o-mail-Message .o-mail-Composer-input", "GoodByeWorld!");
    await animationFrame();
    await advanceTime(SHORT_TYPING / 2);
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await animationFrame();
    await waitFor(`${actionPanel("Members")} [title='Other 10 is typing...']:count(1)`);
    await waitForNone(
        `${actionPanel("Members")} [title='${serverState.partnerName} is typing...']`
    );
});

test.tags("html composer");
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
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMember:count(2)");
    // simulate other user typing
    withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await waitFor(`${actionPanel("Members")} [title='Other 10 is typing...']:count(1)`);
    const threadComposerEditor = {
        document,
        editable: document.querySelector(
            ".o-mail-Composer.o-discussApp .o-mail-Composer-html.odoo-editor-editable"
        ),
    };
    await htmlInsertText(threadComposerEditor, "HelloWorld!");
    await waitFor(
        `${actionPanel("Members")} [title='${serverState.partnerName} is typing...']:count(1)`
    );
    await click(".o-mail-Composer button:enabled[aria-label='Send']");
    await waitForNone(
        `${actionPanel("Members")} [title='${serverState.partnerName} is typing...']`
    );
    await advanceTime(Store.OTHER_LONG_TYPING);
    await waitForNone(`${actionPanel("Members")} [title='Other 10 is typing...']`);
    // check editing doesn't trigger is typing
    await waitFor(".o-mail-Message-content:has(:text('HelloWorld!')):count(1)");
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:text('Edit')");
    await waitFor(".o-mail-Message .o-mail-Composer-html.odoo-editor-editable:count(1)");
    const messageComposerEditor = {
        document,
        editable: document.querySelector(
            ".o-mail-Message .o-mail-Composer-html.odoo-editor-editable"
        ),
    };
    await htmlInsertText(messageComposerEditor, "GoodByeWorld!");
    await animationFrame();
    await advanceTime(SHORT_TYPING / 2);
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await animationFrame();
    await waitFor(`${actionPanel("Members")} [title='Other 10 is typing...']:count(1)`);
    await waitForNone(
        `${actionPanel("Members")} [title='${serverState.partnerName} is typing...']`
    );
});

test("[text composer] switching to another channel triggers notify_typing to stop", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/discuss/channel/notify_typing", (args) =>
        expect.step(`notify_typing:${args.is_typing}`)
    );
    await start();
    await openDiscuss(chatId);
    await insertText(".o-mail-Composer-input", "a");
    await expect.waitForSteps(["notify_typing:true"]);
    await click(".o-mail-MessagingMenu-tab[data-id='channel']");
    await click(".o-mail-NotificationItem:has(:text('general'))");
    await advanceTime(SHORT_TYPING / 2);
    await expect.waitForSteps(["notify_typing:false"]);
});

test.tags("html composer");
test("switching to another channel triggers notify_typing to stop", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Demo", im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", user_ids: [userId] });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["discuss.channel"].create({ name: "general" });
    onRpcBefore("/discuss/channel/notify_typing", (args) =>
        expect.step(`notify_typing:${args.is_typing}`)
    );
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(chatId);
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:count(1)");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "a");
    await expect.waitForSteps(["notify_typing:true"]);
    await click(".o-mail-MessagingMenu-tab[data-id='channel']");
    await click(".o-mail-NotificationItem:has(:text('general'))");
    await advanceTime(SHORT_TYPING / 2);
    await expect.waitForSteps(["notify_typing:false"]);
});
