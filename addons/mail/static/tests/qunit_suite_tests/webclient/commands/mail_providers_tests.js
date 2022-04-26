/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';
import { editSearchBar } from '@web/../tests/core/commands/command_service_tests';
import { click, getFixture, nextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { browser } from '@web/core/browser/browser';
import { commandService } from "@web/core/commands/command_service";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

QUnit.module('mail', {}, function () {
    QUnit.module('Command Palette', {
        beforeEach() {
            serviceRegistry.add("command", commandService);
            patchWithCleanup(browser, {
                clearTimeout() {},
                setTimeout(later, wait) {
                    later();
                },
            });
            registry.category("command_categories").add("default", { label: ("default") });
        },
    });

    QUnit.test('open the chatWindow of a user from the command palette', async function (assert) {
        assert.expect(1);

        const target = getFixture();
        await start({
            target,
        });
        triggerHotkey("control+k");
        await nextTick();

        // Switch to partners
        await editSearchBar("@");

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
        const target = getFixture();
        await start({
            target,
        });
        triggerHotkey("control+k");
        await nextTick();

        // Switch to channels
        await editSearchBar("#");
        assert.deepEqual(
            [...target.querySelectorAll(".o_command_palette .o_command")].map((el) => el.textContent),
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
