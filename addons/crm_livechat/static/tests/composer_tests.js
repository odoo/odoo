/** @odoo-module */

import { afterNextRender, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";
import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("composer");

QUnit.test("Can execute lead command", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start({
        mockRPC(route, args) {
            if (args.method === "execute_command_lead") {
                assert.step("execute_command_lead");
                assert.deepEqual(args.args[0], [channelId]);
                return true;
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "/lead great lead");
    await afterNextRender(() => {
        triggerHotkey("Enter");
    });
    assert.verifySteps(["execute_command_lead"]);
});
