import { test, expect, describe, after } from "@odoo/hoot";
import {
    patchWithCleanup,
    MockServer,
    makeServerError,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { ConnectionLostError } from "@web/core/network/rpc";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

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

    test("getRelatedModels returns the model itself when it has no dependencies", async () => {
        const store = await setupPosEnv();
        const data = store.data;

        // pos.category has no declared dependencies in Python
        const related = data.getRelatedModels("pos.category");
        expect(related).toInclude("pos.category");
    });

    test("getRelatedModels for product.product includes its direct dependencies and reverse", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        // product.product → ['product.template.attribute.value', 'product.template']
        let related = data.getRelatedModels("product.product");
        expect(related).toInclude("product.product");
        expect(related).toInclude("product.template");
        expect(related).toInclude("product.template.attribute.value");

        related = data.getRelatedModels("product.template");
        expect(related).toInclude("product.template");
        expect(related).toInclude("product.product");
        expect(related).toInclude("product.template.attribute.value");
    });

    test("getRelatedModels traverses transitive dependencies", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        // product.product → product.template → account.tax (transitive)
        const related = data.getRelatedModels("product.product");
        expect(related).toInclude("account.tax");
    });

    test("getRelatedModels does not include unrelated models", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        // res.lang has no declared dependency on res.partner and no reverse dependency either
        const related = data.getRelatedModels("res.lang");
        expect(related).not.toInclude("res.partner");
    });

    test("loading a missing product.template also requests product.product", async () => {
        const store = await setupPosEnv();
        const data = store.data;

        const capturedRequests = [];
        patchWithCleanup(data, {
            async callRelated(model, method, args, kwargs, needSync, waitForResult) {
                if (method === "load_data") {
                    capturedRequests.push(args[1]);
                }
                return super.callRelated(...arguments);
            },
        });

        // product_tmpl_id points to a template not yet in the local store
        const fakeProductRecord = MockServer.env["product.template"].create({
            list_price: 10,
            name: "Missing Product",
        });

        await data.loadRecordsFromPos(["product.template"], {
            "product.template": [["id", "=", fakeProductRecord.id]],
        });

        expect(capturedRequests.length).toBeGreaterThan(0);
        const allRequestedModels = capturedRequests.flatMap((req) => req.models);
        expect(allRequestedModels).toInclude("product.product");
    });

    describe("syncData", () => {
        const queueWrites = async (data, partners) => {
            data.network.offline = true;
            for (const partner of partners) {
                await data.ormWrite("res.partner", [partner.id], { name: `Offline ${partner.id}` });
            }
            data.network.offline = false;
            expect(data.network.unsyncData).toHaveLength(partners.length);
        };

        test("a failing queued operation is discarded and does not block the next ones", async () => {
            const store = await setupPosEnv();
            const data = store.data;
            const [failing, other] = store.models["res.partner"].getAll();
            onRpc("res.partner", "write", ({ args }) => {
                expect.step(`write ${args[0]}`);
                if (args[0][0] === failing.id) {
                    throw makeServerError({ type: "MissingError", message: "Record deleted" });
                }
                return true;
            });
            await queueWrites(data, [failing, other]);

            await data.syncData();

            expect.verifySteps([`write ${failing.id}`, `write ${other.id}`]);
            expect(data.network.unsyncData).toHaveLength(0);
            expect(data.syncInProgress()).toBe(false);
        });

        test("a queued call returning false does not block the queue", async () => {
            const store = await setupPosEnv();
            const data = store.data;
            onRpc("pos.session", "do_nothing", () => false);
            data.network.offline = true;
            await data.call("pos.session", "do_nothing", [[1]], {}, true);
            data.network.offline = false;
            expect(data.network.unsyncData).toHaveLength(1);

            await data.syncData();

            expect(data.network.unsyncData).toHaveLength(0);
        });

        test("a connection loss during the replay keeps the queue", async () => {
            const store = await setupPosEnv();
            const data = store.data;
            const partners = store.models["res.partner"].getAll().slice(0, 2);
            await queueWrites(data, partners);
            patchWithCleanup(data.orm, {
                write() {
                    return Promise.reject(new ConnectionLostError("/web/dataset/call_kw"));
                },
            });

            await expect(data.syncData()).rejects.toThrow(ConnectionLostError);

            expect(data.network.unsyncData).toHaveLength(2);
            expect(data.syncInProgress()).toBe(false);
        });

        test("an offline write notifies the other devices once replayed", async () => {
            const store = await setupPosEnv();
            const data = store.data;
            const [partner] = store.models["res.partner"].getAll();
            onRpc("res.partner", "write", () => {
                expect.step("write");
                return true;
            });
            onRpc("pos.config", "notify_synchronisation", () => {
                expect.step("notify_synchronisation");
                return true;
            });
            await queueWrites(data, [partner]);
            expect.verifySteps([]);

            await data.syncData();

            await expect.waitForSteps(["write", "notify_synchronisation"]);
        });

        test("back online is notified even if a queued operation fails", async () => {
            const store = await setupPosEnv();
            const data = store.data;
            const [failing] = store.models["res.partner"].getAll();
            onRpc("/pos/ping", () => true);
            onRpc("res.partner", "write", () => {
                throw makeServerError({ type: "MissingError" });
            });
            await queueWrites(data, [failing]);
            const onOnline = () => expect.step("pos-network-online");
            window.addEventListener("pos-network-online", onOnline);
            after(() => window.removeEventListener("pos-network-online", onOnline));

            await data.checkConnectivity();

            expect.verifySteps(["pos-network-online"]);
            expect(data.network.unsyncData).toHaveLength(0);
        });
    });
});
