/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { busService } from "@bus/services/bus_service";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";
import { nextTick, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

QUnit.module("discuss");

QUnit.test("Member list and settings menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList");
    await click("[title='Show Call Settings']");
    await contains(".o-discuss-CallSettings");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
});

QUnit.test("subscribe to presence channels according to store data", async (assert) => {
    const busServiceStartDeferred = new Deferred();
    registry.category("services").add(
        "bus_service",
        {
            dependencies: busService.dependencies,
            start() {
                const ogAPI = busService.start(...arguments);
                patchWithCleanup(ogAPI, {
                    async start() {
                        await busServiceStartDeferred;
                        return super.start();
                    },
                });
                return ogAPI;
            },
        },
        { force: true }
    );
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                step(`subscribe - [${data.channels}]`);
            }
        },
    });
    const { env } = await start();
    const store = env.services["mail.store"];
    assert.notOk(env.services.bus_service.isActive);
    // Should not subscribe to presences as bus service is not started.
    await nextTick();
    await assertSteps([]);
    // Starting the bus should subscribe to known presence channels.
    busServiceStartDeferred.resolve();
    await assertSteps([`subscribe - [odoo-presence-res.partner_${store.self.id}]`]);
    // Discovering new presence channels should refresh the subscription.
    store["Persona"].insert({ id: 5000, type: "partner", name: "Partner 5000" });
    await assertSteps([
        `subscribe - [odoo-presence-res.partner_${store.self.id},odoo-presence-res.partner_5000]`,
    ]);
    store["Persona"].insert({ id: 1, type: "guest" });
    await assertSteps([
        `subscribe - [odoo-presence-mail.guest_1,odoo-presence-res.partner_${store.self.id},odoo-presence-res.partner_5000]`,
    ]);
});

QUnit.test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name }) {
            if (event_name === "subscribe") {
                step("subscribe");
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { openDiscuss } = await start();
    await openDiscuss();
    await assertSteps(["subscribe"]);
    await click(".o-mail-DiscussSidebar i[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "new channel");
    await click(".o-discuss-ChannelSelector-suggestion");
    await assertSteps(["subscribe"]);
});

QUnit.test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name }) {
            if (event_name === "subscribe") {
                step("subscribe");
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { openDiscuss } = await start();
    await assertSteps(["subscribe"]);
    await openDiscuss();
    await assertSteps([]);
    await click("[title='Leave this channel']");
    await assertSteps(["subscribe"]);
});
