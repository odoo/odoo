import { test, expect, describe } from "@odoo/hoot";
import { MockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { getTemplate } from "@web/core/templates";
import { ConnectionLostError } from "@web/core/network/rpc";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { parseWriteDateTimestamp } from "@point_of_sale/app/plugins/pos_data_plugin";

definePosModels();

describe("data_service", () => {
    test("an unreachable server registers the receipt templates stored in indexedDB", async () => {
        const store = await setupPosEnv();
        const views = [{ id: "offline", key: "pos.offline_receipt", _template: "<div/>" }];
        patch(store.data.orm, {
            call: () => Promise.reject(new ConnectionLostError("/web/dataset/call_kw")),
        });
        patch(store.data, {
            getCachedServerDataFromIndexedDB: async () => ({ "ir.ui.view": views }),
        });

        await store.data.initData();

        expect(getTemplate("pos.offline_receipt")).not.toBe(null);
    });

    test("the receipt templates of the server replace the ones stored in indexedDB", async () => {
        const store = await setupPosEnv();
        const key = "point_of_sale.pos_order_receipt";
        const views = [{ id: "old", key, _template: "<div>old</div>" }];
        patch(store.data, {
            getCachedServerDataFromIndexedDB: async () => ({ "ir.ui.view": views }),
        });

        await store.data.initData();

        expect(getTemplate(key).outerHTML).not.toInclude("<div>old</div>");
    });

    test("a full local storage does not block the opening", async () => {
        const store = await setupPosEnv();
        patchWithCleanup(localStorage, {
            setItem() {
                throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
            },
        });
        patchWithCleanup(window, { alert: (message) => expect.step(message) });
        patchWithCleanup(store.data.notification, {
            add: (message, options) => expect.step([message.toString(), options.type]),
        });

        const data = await store.data.loadInitialData();

        expect.verifySteps([
            [
                "The browser storage is full: new orders may not be created. Ask your administrator to free some space in this browser.",
                "warning",
            ],
        ]);
        expect(data["pos.config"]).toHaveLength(1);
    });

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
        patch(data, {
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

    test("getModelsLoadedWith a product: its own models, not the customers and orders", async () => {
        const store = await setupPosEnv();
        const models = store.data.getModelsLoadedWith("product.template");
        for (const model of [
            "product.template",
            "product.product",
            "product.template.attribute.line",
            "product.template.attribute.value",
            "product.attribute",
            "product.pricelist.item",
            "product.pricelist",
            "account.tax",
        ]) {
            expect(models).toInclude(model);
        }
        for (const model of ["pos.preset", "account.fiscal.position", "res.partner", "pos.order"]) {
            expect(models).not.toInclude(model);
        }
    });

    test("loading new products neither asks for nor sends the cached customers", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        const requests = [];
        patch(data, {
            async callRelated(model, method, args, kwargs, needSync, waitForResult) {
                if (method === "load_data") {
                    requests.push(args[1]);
                }
                return super.callRelated(...arguments);
            },
        });
        const template = MockServer.env["product.template"].create({
            list_price: 10,
            name: "Not loaded yet",
        });

        await store.loadNewProducts([["id", "=", template.id]]);

        expect(requests.length).toBe(1);
        expect(requests[0].models).toInclude("product.product");
        expect(requests[0].models).not.toInclude("res.partner");
        expect(requests[0].models).not.toInclude("pos.order");
        expect(Object.keys(requests[0].records)).not.toInclude("res.partner");
    });

    test("loadRecordsFromPos does not read indexedDB for models filtered by a domain", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        const requests = [];
        const cachedModelsRead = [];
        patch(data, {
            async getCachedServerIdsFromIndexedDB(models) {
                cachedModelsRead.push(models);
                return super.getCachedServerIdsFromIndexedDB(...arguments);
            },
            async callRelated(model, method, args) {
                if (method === "load_data") {
                    requests.push(args[1]);
                }
                return super.callRelated(...arguments);
            },
        });
        const template = MockServer.env["product.template"].create({
            list_price: 10,
            name: "Scanned product",
        });

        await store.loadNewProducts([["id", "=", template.id]]);

        expect(cachedModelsRead.length).toBe(1);
        expect(cachedModelsRead[0]).not.toInclude("product.template");
        expect(cachedModelsRead[0]).toInclude("product.product");
        expect(Object.keys(requests[0].records)).not.toInclude("product.template");

        cachedModelsRead.length = 0;
        await data.loadRecordsFromPos(
            ["res.partner"],
            { "res.partner": [["id", "=", 1]] },
            {},
            {},
            {},
            false
        );
        expect(cachedModelsRead).toEqual([]);

        // missingRecursive also skips IndexedDB for models filtered by search_params.domain
        const missingPartner = MockServer.env["res.partner"].create({ name: "Missing partner" });
        const order = await getFilledOrder(store);
        await data.missingRecursive({
            "pos.order": [{ ...order.raw, id: 5001, partner_id: missingPartner }],
        });
        expect(cachedModelsRead.length).toBe(1);
        expect(cachedModelsRead[0]).not.toInclude("res.partner");
    });

    test("indexedDB is not read again for the write dates of what is already known", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        const order = await getFilledOrder(store);
        const cachedData = { "ir.ui.view": [] };
        localStorage.setItem(`pos_data_params_${odoo.pos_config_id}`, "{}");
        patch(data, {
            getCachedServerDataFromIndexedDB: async () => cachedData,
            async getCachedServerIdsFromIndexedDB(models, cached) {
                expect.step({ models, cached: cached === cachedData });
                return super.getCachedServerIdsFromIndexedDB(...arguments);
            },
        });

        await data.missingRecursive({
            "pos.order": [{ ...order.raw, id: 5000 }],
            "pos.order.line": order.lines.map((line) => ({ ...line.raw, order_id: 5000 })),
        });
        expect.verifySteps([]);

        await data.initData();
        expect.verifySteps([{ models: [], cached: true }]);
    });

    test("syncInitialData only writes records returned by the server to indexedDB", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        const written = [];
        patchWithCleanup(data, {
            async cleanOldModels() {},
            async synchronizeServerDataInIndexedDB(serverData) {
                written.push(serverData);
            },
        });
        patchWithCleanup(data.indexedDB, {
            delete() {},
        });

        const localData = {
            "res.partner": [
                { id: 1, name: "Cached Partner" },
                { id: 2, name: "Removed Partner" },
            ],
            "product.template": [{ id: 10, name: "Cached Product" }],
        };
        const serverData = {
            "res.partner": {
                records: [{ id: 3, name: "New Partner" }],
                to_remove: [2],
            },
            "product.template": {
                records: [],
                to_remove: [],
            },
        };

        await data.syncInitialData(serverData, localData);

        expect(written).toEqual([{ "res.partner": [{ id: 3, name: "New Partner" }] }]);
        expect(localData["res.partner"].map((r) => r.id)).toEqual([1, 3]);
        expect(localData["product.template"].map((r) => r.id)).toEqual([10]);

        written.length = 0;
        await data.syncInitialData(
            { "product.template": { records: [], to_remove: [] } },
            localData
        );
        expect(written).toEqual([]);
    });

    test("parseWriteDateTimestamp matches deserializeDateTime", () => {
        for (const value of [
            "2026-11-24 10:15:30",
            "2026-11-24 10:15:30.5",
            "2026-11-24 10:15:30.12",
            "2026-11-24 10:15:30.123456",
            "2024-02-29 23:59:59.999999",
            "2026-11-24 10:15:30+02:00",
        ]) {
            expect(parseWriteDateTimestamp(value)).toBe(
                deserializeDateTime(value).toMillis() / 1000
            );
        }
        for (const value of [false, null, undefined, ""]) {
            const before = Date.now() / 1000;
            const timestamp = parseWriteDateTimestamp(value);
            expect(timestamp >= before && timestamp <= Date.now() / 1000).toBe(true);
        }
        expect(parseWriteDateTimestamp("invalid")).toBe(0);
    });

    test("websocket reconnections don't duplicate the notification listeners", async () => {
        const store = await setupPosEnv();
        const bus = store.data.bus;
        let addedListeners = 0;
        patch(bus, {
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
        bus.handleMessage({ data: { type: "BUS:CONNECT" } });
        bus.handleMessage({ data: { type: "BUS:CONNECT" } });
        expect.verifySteps(["addChannel", "addChannel"]);
        expect(addedListeners).toBe(0);
    });
});
