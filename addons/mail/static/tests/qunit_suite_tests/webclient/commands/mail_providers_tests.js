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
        assert.expect(3);

        const pyEnv = await startServer();
        const [resPartnerId1, resPartnerId2, resPartnerId3] = pyEnv['res.partner'].create([
            { name: "Partner 1", email: "p1@odoo.com" },
            { name: "Partner 2", email: "p2@odoo.com" },
            { name: "Partner 3", email: "p3@odoo.com" },
        ]);
        pyEnv['res.users'].create([
            { name: "User 1", partner_id: resPartnerId1 },
            { name: "User 2", partner_id: resPartnerId2 },
            { name: "User 3", partner_id: resPartnerId3 },
        ]);

        const target = getFixture();
        await start({
            hasChatWindow: true,
            hasWebClient: true,
            target,
        });
        triggerHotkey("control+k");
        await nextTick();

        // Switch to partners
        await editSearchBar("@");
        assert.deepEqual(
            [...target.querySelectorAll(".o_command_palette .o_command")].map((el) => el.textContent),
            [
                "Partner 1p1@odoo.com",
                "Partner 2p2@odoo.com",
                "Partner 3p3@odoo.com",
            ]
        );

        await afterNextRender(() => click(document.body, ".o_command.focused"));
        assert.containsOnce(document.body, ".o_ChatWindow");
        assert.strictEqual(document.querySelector(".o_ChatWindow .o_ChatWindowHeader_name").textContent, "Partner 1");
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
            hasChatWindow: true,
            hasWebClient: true,
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
