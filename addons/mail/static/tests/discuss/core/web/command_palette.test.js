import {
    click,
    contains,
    defineMailModels,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { registry } from "@web/core/registry";
import { advanceTime } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

const commandSetupRegistry = registry.category("command_setup");

test("open the chatWindow of a user from the command palette", async () => {
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await contains(".o_command", { count: 2 });
    await click(".o_command.focused", { text: "Mitchell Admin" });
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin" });
});

test("open the chatWindow of a channel from the command palette", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-02 10:00:00", // same last interest to sort by id
            }),
        ],
    });
    pyEnv["discuss.channel"].create({
        name: "project",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-02 10:00:00", // same last interest to sort by id
            }),
        ],
    });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "#");
    await contains(".o_command", { count: 2 });
    await contains(".o_command", { text: "project", before: [".o_command", { text: "general" }] });
    await contains(".o_command.focused");
    await click(".o_command.focused", { text: "project" });
    await contains(".o-mail-ChatWindow", { text: "project" });
});

test("Channel mentions in the command palette of Discuss app with @", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "@Mitchell Admin",
        needaction: true,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@", { replace: true });
    await contains(".o_command_palette .o_command_category", {
        contains: [
            ["span.fw-bold", { text: "Mentions" }],
            [".o_command.focused .o_command_name", { text: "Mitchell Admin and Mario" }],
        ],
    });
    await contains(".o_command_palette .o_command_category", {
        contains: [[".o_command_name", { text: "Mitchell Admin" }]],
    });
    await click(".o_command.focused");
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin and Mario" });
});

test("Max 3 most recent channels in command palette of Discuss app with #", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "channel_1" });
    pyEnv["discuss.channel"].create({ name: "channel_2" });
    pyEnv["discuss.channel"].create({ name: "channel_3" });
    pyEnv["discuss.channel"].create({ name: "channel_4" });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "#", { replace: true });
    await contains(".o_command_palette .o_command_category", {
        contains: [
            ["span.fw-bold", { text: "Recent" }],
            [".o_command", { count: 3 }],
        ],
    });
});

test("only partners with dedicated users will be displayed in command palette", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test user" });
    pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    advanceTime(commandSetupRegistry.get("@").debounceDelay);
    await contains(".o_command_name", { text: "Mitchell Admin" });
    await contains(".o_command_name", { text: "OdooBot" });
    await contains(".o_command_name", { text: "test user", count: 0 });
});
