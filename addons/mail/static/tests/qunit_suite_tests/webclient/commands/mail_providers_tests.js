/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';
import { editSearchBar } from '@web/../tests/core/commands/command_service_tests';
import { click, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { commandService } from "@web/core/commands/command_service";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");
const commandSetupRegistry = registry.category("command_setup");

QUnit.module('mail', {}, function () {
    QUnit.module('webclient', function () {
    QUnit.module('commands', function () {
    QUnit.module('mail_providers_tests.js', {
        beforeEach() {
            serviceRegistry.add("command", commandService);
            registry.category("command_categories").add("default", { label: ("default") });
        },
    });

    QUnit.test('open the chatWindow of a user from the command palette', async function (assert) {
        assert.expect(1);

        const { advanceTime } = await start({
            hasTimeControl: true,
        });
        triggerHotkey("control+k");
        await nextTick();

        // Switch to partners
        await editSearchBar("@");
        await afterNextRender(() => advanceTime(commandSetupRegistry.get('@').debounceDelay));

        await afterNextRender(() => click(document.body, ".o_command.focused"));
        assert.containsOnce(document.body, ".o_ChatWindow");
    });

    QUnit.test('open the chatWindow of a channel from the command palette', async function (assert) {
        assert.expect(3);

        const pyEnv = await startServer();
        pyEnv['mail.channel'].create({
            name: "general",
        });
        pyEnv['mail.channel'].create({
            name: "project",
        });
        const { advanceTime } = await start({
            hasTimeControl: true,
        });
        triggerHotkey("control+k");
        await nextTick();

        // Switch to channels
        await editSearchBar("#");
        await afterNextRender(() => advanceTime(commandSetupRegistry.get('#').debounceDelay));

        assert.deepEqual(
            [...document.querySelectorAll(".o_command_palette .o_command")].map((el) => el.textContent),
            [
                "general",
                "project"
            ],
        );

        await afterNextRender(() => click(document.body, ".o_command.focused"));
        assert.containsOnce(document.body, ".o_ChatWindow");
        assert.strictEqual(document.querySelector(".o_ChatWindow .o_ChatWindowHeader_name").textContent, "general");
    });

    });
    });
});
