/* @odoo-module */

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { triggerHotkey, patchWithCleanup } from "@web/../tests/helpers/utils";

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
    await openDiscuss();
    await click("[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector", "General");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.verifySteps(["update-channels"]);
});
