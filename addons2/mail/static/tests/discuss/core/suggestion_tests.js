/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("suggestion", {
    async beforeEach() {
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test('display command suggestions on typing "/"', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("use a command for a specific channel type", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "/");
    await click(".o-mail-Composer-suggestion strong", { text: "who" });
    await contains(".o-mail-Composer-input", { value: "/who " });
});

QUnit.test("command suggestion should only open if command is the first character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    await contains(".o-mail-Composer-input", { value: "bluhbluh " });
    await insertText(".o-mail-Composer-input", "/");
    // weak test, no guarantee that we waited long enough for the potential list to open
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
});

QUnit.test("Sort partner suggestions by recent chats", async () => {
    const pyEnv = await startServer();
    const [partner_1, partner_2, partner_3] = pyEnv["res.partner"].create([
        { name: "User 1" },
        { name: "User 2" },
        { name: "User 3" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partner_1 },
        { partner_id: partner_2 },
        { partner_id: partner_3 },
    ]);
    pyEnv["discuss.channel"].create([
        {
            name: "General",
            channel_type: "channel",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partner_1 }),
                Command.create({ partner_id: partner_2 }),
                Command.create({ partner_id: partner_3 }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partner_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partner_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partner_3 }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "User 2" });
    await insertText(".o-mail-Composer-input", "This is a test");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content", { text: "This is a test" });
    await click(".o-mail-DiscussSidebarChannel", { text: "General" });
    await insertText(".o-mail-Composer-input[placeholder='Message #General…']", "@");
    await insertText(".o-mail-Composer-input", "User");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
    await contains(":nth-child(1 of .o-mail-Composer-suggestion) strong", { text: "User 2" });
    await contains(":nth-child(2 of .o-mail-Composer-suggestion) strong", { text: "User 3" });
    await contains(":nth-child(3 of .o-mail-Composer-suggestion) strong", { text: "User 1" });
});

QUnit.test("mention suggestion are shown after deleting a character", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@John D");
    await contains(".o-mail-Composer-suggestion strong", { text: "John Doe" });
    await insertText(".o-mail-Composer-input", "a");
    await contains(".o-mail-Composer-suggestion strong", { count: 0, text: "John D" });

    // Simulate pressing backspace
    const textarea = document.querySelector(".o-mail-Composer-input");
    textarea.value = textarea.value.slice(0, -1);
    await contains(".o-mail-Composer-suggestion strong", { text: "John Doe" });
});

QUnit.test("command suggestion are shown after deleting a character", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/he");
    await contains(".o-mail-Composer-suggestion strong", { text: "help" });
    await insertText(".o-mail-Composer-input", "e");
    await contains(".o-mail-Composer-suggestion strong", { count: 0, text: "help" });

    // Simulate pressing backspace
    const textarea = document.querySelector(".o-mail-Composer-input");
    textarea.value = textarea.value.slice(0, -1);
    await contains(".o-mail-Composer-suggestion strong", { text: "help" });
});

QUnit.test("mention suggestion displays OdooBot before archived partners", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane", active: false });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Our channel",
        channel_type: "group",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
            Command.create({ partner_id: pyEnv.odoobotId }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 3 });
    await contains(".o-mail-Composer-suggestion", {
        text: "Mitchell Admin",
        before: [
            ".o-mail-Composer-suggestion",
            {
                text: "OdooBot",
                before: [".o-mail-Composer-suggestion", { text: "Jane" }],
            },
        ],
    });
});
