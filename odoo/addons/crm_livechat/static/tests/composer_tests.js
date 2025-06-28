/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, insertText } from "@web/../tests/utils";

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
    await click(".o-mail-Composer-send:enabled");
    assert.verifySteps(["execute_command_lead"]);
});
