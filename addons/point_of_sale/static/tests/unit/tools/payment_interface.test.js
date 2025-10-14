import { describe, expect, test } from "@odoo/hoot";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("connectWebsocket", () => {
    test("can subscribe to a websocket channel", async () => {
        const store = await setupPosEnv();
        const paymentInterface = new PaymentInterface(store);

        paymentInterface.connectWebSocket("testChannel", () => {});

        const subscribedChannels = store.data.channels.map((channelInfo) => channelInfo.channel);
        expect(subscribedChannels).toInclude("testChannel");
    });

    test("can subscribe to multiple channels", async () => {
        const store = await setupPosEnv();
        const paymentInterface = new PaymentInterface(store);

        paymentInterface.connectWebSocket("testChannel", () => {});
        paymentInterface.connectWebSocket("testChannel2", () => {});

        const subscribedChannels = store.data.channels.map((channelInfo) => channelInfo.channel);
        expect(subscribedChannels).toInclude("testChannel");
        expect(subscribedChannels).toInclude("testChannel2");
    });

    test("only subscribes once to a given channel if called multiple times", async () => {
        const store = await setupPosEnv();
        const paymentInterface = new PaymentInterface(store);

        paymentInterface.connectWebSocket("testChannel", () => {});
        paymentInterface.connectWebSocket("testChannel", () => {});

        const subscribedTestChannels = store.data.channels
            .map((channelInfo) => channelInfo.channel)
            .filter((channel) => channel === "testChannel");
        expect(subscribedTestChannels).toHaveLength(1);
    });
});
