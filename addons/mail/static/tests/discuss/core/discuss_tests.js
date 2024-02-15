/* @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";
import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { assertSteps, click as clickContains, insertText, step } from "@web/../tests/utils";
import { patchDate } from "@web/../tests/helpers/utils";

QUnit.module("discuss");

QUnit.test("Member list and settings menu are exclusive", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    assert.containsOnce($, ".o-discuss-ChannelMemberList");
    await click("[title='Show Call Settings']");
    assert.containsOnce($, ".o-discuss-CallSettings");
    assert.containsNone($, ".o-discuss-ChannelMemberList");
});

QUnit.test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                step(`subscribe - ${JSON.stringify(data.channels)}`);
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { openDiscuss } = await start();
    await assertSteps(["subscribe - []"]);
    await openDiscuss();
    await assertSteps([]);
    await clickContains(".o-mail-DiscussSidebar i[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "new channel");
    await clickContains(".o-discuss-ChannelSelector-suggestion");
    await assertSteps(["subscribe - []"]);
});

QUnit.test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                step(`subscribe - ${JSON.stringify(data.channels)}`);
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { openDiscuss } = await start();
    await assertSteps(["subscribe - []"]);
    await openDiscuss();
    await assertSteps([]);
    await clickContains("[title='Leave this channel']");
    await assertSteps(["subscribe - []"]);
});
