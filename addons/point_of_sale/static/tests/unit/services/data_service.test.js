import { test, expect, describe } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

describe("data_service", () => {
    test("localDeleteCascade", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        const order = await getFilledOrder(store);

        expect(store.models["pos.order"].length).toBe(1);
        expect(store.models["pos.order.line"].length).toBe(2);
        data.localDeleteCascade(order);
        expect(store.models["pos.order"].length).toBe(0);
        expect(store.models["pos.order.line"].length).toBe(0);
    });

    test("websocket reconnections don't duplicate the notification listeners", async () => {
        const store = await setupPosEnv();
        const bus = store.data.bus;
        let addedListeners = 0;
        patchWithCleanup(bus, {
            addChannel(channel) {
                if (channel === odoo.access_token) {
                    expect.step("addChannel");
                }
                return super.addChannel(...arguments);
            },
            subscribe() {
                addedListeners++;
                return super.subscribe(...arguments);
            },
            unsubscribe() {
                addedListeners--;
                return super.unsubscribe(...arguments);
            },
        });

        // Going offline then online again triggers a "BUS:CONNECT" event on each reconnection
        bus.trigger("BUS:CONNECT");
        bus.trigger("BUS:CONNECT");
        expect.verifySteps(["addChannel", "addChannel"]);
        expect(addedListeners).toBe(0);
    });
});
