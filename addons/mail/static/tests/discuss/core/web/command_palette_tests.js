/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { commandService } from "@web/core/commands/command_service";
import { registry } from "@web/core/registry";
import { Command } from "@mail/../tests/helpers/command";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

const serviceRegistry = registry.category("services");
const commandSetupRegistry = registry.category("command_setup");

QUnit.module("command palette", {
    async beforeEach() {
        serviceRegistry.add("command", commandService);
        registry.category("command_categories").add("default", { label: "default" });
    },
});

QUnit.test("open the chatWindow of a user from the command palette", async () => {
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    advanceTime(commandSetupRegistry.get("@").debounceDelay);
    await contains(".o_command", { count: 1 });
    await click(".o_command.focused", { text: "Mitchell Admin" });
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin" });
});

QUnit.test("open the chatWindow of a channel from the command palette", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["discuss.channel"].create({ name: "project" });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "#");
    advanceTime(commandSetupRegistry.get("#").debounceDelay);
    await contains(".o_command", { count: 2 });
    await click(".o_command.focused", { text: "general" });
    await contains(".o-mail-ChatWindow", { text: "general" });
});

QUnit.test("only partners with dedicated users will be displayed in command palette", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test user" });
    pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    advanceTime(commandSetupRegistry.get("@").debounceDelay);
    await contains(".o_command_name", { text: "Mitchell Admin" });
    await contains(".o_command_name", { text: "OdooBot" });
    await contains(".o_command_name", { text: "test user", count: 0 });
});
