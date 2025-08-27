import { test, expect, describe } from "@odoo/hoot";
import { patchWithCleanup, MockServer } from "@web/../tests/web_test_helpers";
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
});
