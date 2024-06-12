/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("crosstab");

QUnit.test("Channel subscription is renewed when channel is manually added", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General", channel_member_ids: [] });
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            assert.step("update-channels");
        },
    });
    openDiscuss();
    await click("[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "General");
    await click(":nth-child(1 of .o-discuss-ChannelSelector-suggestion)");
    await contains(".o-mail-DiscussSidebarChannel", { count: 1 });
    await new Promise((resolve) => setTimeout(resolve)); // update of channels is debounced
    assert.verifySteps(["update-channels"]);
});
