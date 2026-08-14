import { beforeEach, expect, runAllTimers, test } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";
import { definePosModels } from "../data/generate_model_definitions";
import { setupPosEnv } from "../utils";

definePosModels();

const displayAnnounces = (store, action, device_id = "display-device-1") =>
    store.customerDisplay.trackDevice({ action, device_id });

/**
 * Steps every announcement reaching the registration route, and every dispatch
 * reaching the customer display, so the tests assert on the requests actually
 * made rather than on internal state.
 */
beforeEach(() => {
    onRpc("/pos_customer_display/register-device", async (request) => {
        const { params } = await request.json();
        expect.step(`announce:${params.payload.action}`);
        return true;
    });
    onRpc("pos.config", "update_customer_display", () => {
        expect.step("update_customer_display");
        return true;
    });
});

test("terminal asks who is connected when it starts", async () => {
    const store = await setupPosEnv();
    await runAllTimers();

    // A display already open cannot know a new terminal appeared, so asking is
    // the terminal's job. Announcing ADD/REMOVE is the display's.
    expect.verifySteps(["announce:PING"]);
    expect(store.customerDisplay.hasConnectedDisplay).toBe(false);
});

test("terminal ignores the echo of its own ping", async () => {
    const store = await setupPosEnv();
    await runAllTimers();
    expect.verifySteps(["announce:PING"]);

    // The ping is broadcast on the config channel, so it comes back. It carries
    // no device id, which is how the terminal tells it apart from a display.
    store.customerDisplay.trackDevice({ action: "PING" });
    expect(store.customerDisplay.hasConnectedDisplay).toBe(false);
});

test("a new order asks again while no display is connected", async () => {
    const store = await setupPosEnv();
    await runAllTimers();
    expect.verifySteps(["announce:PING"]);

    // An announcement can be missed, so a new order is a second chance to
    // notice a display that was already there.
    store.addNewOrder();
    await runAllTimers();
    expect.verifySteps(["announce:PING"]);

    // Once one is known there is nothing left to discover, and the new order is
    // dispatched instead.
    displayAnnounces(store, "ADD");
    const order = store.addNewOrder();
    await runAllTimers();
    expect.verifySteps(["update_customer_display"]);

    // The display page is closed or frozen, and says so on its way out.
    displayAnnounces(store, "REMOVE");
    expect(store.customerDisplay.hasConnectedDisplay).toBe(false);
    store.customerDisplay.sendOrder(order);
    await runAllTimers();
    expect.verifySteps([]);
});

test("terminal counts each display separately", async () => {
    const store = await setupPosEnv();
    await runAllTimers();
    expect.verifySteps(["announce:PING"]);

    displayAnnounces(store, "ADD", "display-1");
    displayAnnounces(store, "ADD", "display-2");
    expect(store.customerDisplay.connectedDevices().size).toBe(2);

    // One display leaving does not silence the terminal for the other.
    displayAnnounces(store, "REMOVE", "display-1");
    expect(store.customerDisplay.hasConnectedDisplay).toBe(true);

    displayAnnounces(store, "REMOVE", "display-2");
    expect(store.customerDisplay.hasConnectedDisplay).toBe(false);
});

test("a display announces itself when it opens", async () => {
    await setupPosEnv();
    await runAllTimers();
    expect.verifySteps(["announce:PING"]);

    await mountWithCleanup(CustomerDisplay);
    await runAllTimers();
    expect.verifySteps(["announce:ADD"]);
});
