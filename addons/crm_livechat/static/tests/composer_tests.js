/* @odoo-module */

import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("composer");

QUnit.test("Can execute lead command", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
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
    await insertText(".o-mail-Composer-input", "/lead great lead");
    await click(".o-mail-Composer-send:not(:disabled)");
    assert.verifySteps(["execute_command_lead"]);
});
