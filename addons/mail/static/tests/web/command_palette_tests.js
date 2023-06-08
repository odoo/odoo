/* @odoo-module */

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { commandService } from "@web/core/commands/command_service";
import { registry } from "@web/core/registry";
import { editSearchBar } from "@web/../tests/core/commands/command_service_tests";
import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");
const commandSetupRegistry = registry.category("command_setup");

QUnit.module("command palette", {
    async beforeEach() {
        serviceRegistry.add("command", commandService);
        registry.category("command_categories").add("default", { label: "default" });
    },
});

QUnit.test("open the chatWindow of a user from the command palette", async (assert) => {
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await nextTick();
    // Switch to partners
    await editSearchBar("@");
    await afterNextRender(() => advanceTime(commandSetupRegistry.get("@").debounceDelay));
    await click(".o_command.focused");
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test("open the chatWindow of a channel from the command palette", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["discuss.channel"].create({ name: "project" });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await nextTick();
    // Switch to channels
    await editSearchBar("#");
    await afterNextRender(() => advanceTime(commandSetupRegistry.get("#").debounceDelay));
    assert.containsOnce($, ".o_command:contains(general)");
    assert.containsOnce($, ".o_command:contains(project)");

    await click(".o_command.focused");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow-name:contains(general)");
});
