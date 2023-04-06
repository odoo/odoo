/** @odoo-module **/

import { fieldService } from "@web/core/field_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

function getModelInfo(resModel) {
    return {
        resModel,
        fieldDefs: serverData.models[resModel].fields,
    };
}

let serverData;
QUnit.module("Field Service", {
    async beforeEach() {
        serverData = {
            models: {
                tortoise: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        age: { type: "integer", string: "Age" },
                        location_id: { type: "many2one", string: "Location", relation: "location" },
                    },
                },
                location: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        tortoise_ids: { type: "one2many", string: "Turtles", relation: "tortoise" },
                    },
                },
            },
        };
        serviceRegistry.add("field", fieldService);
    },
});

QUnit.test("loadPath", async (assert) => {
    const toTest = [
        {
            resModel: "tortoise",
            path: "*",
            expectedResult: {
                names: ["*"],
                modelsInfo: [getModelInfo("tortoise")],
            },
        },
        {
            resModel: "tortoise",
            path: "*.a",
            expectedResult: {
                isInvalid: "path",
                names: ["*", "a"],
                modelsInfo: [getModelInfo("tortoise")],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.*",
            expectedResult: {
                names: ["location_id", "*"],
                modelsInfo: [getModelInfo("tortoise"), getModelInfo("location")],
            },
        },
        {
            resModel: "tortoise",
            path: "age",
            expectedResult: {
                names: ["age"],
                modelsInfo: [getModelInfo("tortoise")],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id",
            expectedResult: {
                names: ["location_id"],
                modelsInfo: [getModelInfo("tortoise")],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.tortoise_ids",
            expectedResult: {
                names: ["location_id", "tortoise_ids"],
                modelsInfo: [getModelInfo("tortoise"), getModelInfo("location")],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.tortoise_ids.age",
            expectedResult: {
                names: ["location_id", "tortoise_ids", "age"],
                modelsInfo: [
                    getModelInfo("tortoise"),
                    getModelInfo("location"),
                    getModelInfo("tortoise"),
                ],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.tortoise_ids.age",
            expectedResult: {
                names: ["location_id", "tortoise_ids", "age"],
                modelsInfo: [
                    getModelInfo("tortoise"),
                    getModelInfo("location"),
                    getModelInfo("tortoise"),
                ],
            },
        },
    ];

    const env = await makeTestEnv({ serverData });

    for (const { resModel, path, expectedResult } of toTest) {
        const result = await env.services.field.loadPath(resModel, path);
        assert.deepEqual(result, expectedResult);
    }

    const errorToTest = [
        { resModel: "notAModel" },
        { resModel: "tortoise", path: {} },
        { resModel: "tortoise", path: "" },
    ];

    for (const { resModel, path } of errorToTest) {
        try {
            await env.services.field.loadPath(resModel, path);
        } catch {
            assert.step("error");
        }
    }
    assert.verifySteps(errorToTest.map(() => "error"));
});

QUnit.test("store loadFields calls in cache in success", async (assert) => {
    assert.expect(2);

    const mockRPC = (route) => {
        if (route.includes("fields_get")) {
            assert.step("fields_get");
        }
    };

    const env = await makeTestEnv({ serverData, mockRPC });

    await env.services.field.loadFields("tortoise");
    await env.services.field.loadFields("tortoise");

    assert.verifySteps(["fields_get"]);
});

QUnit.test("does not store loadFields calls in cache when failed", async (assert) => {
    assert.expect(5);

    const mockRPC = (route) => {
        if (route.includes("fields_get")) {
            assert.step("fields_get");
            return Promise.reject("my little error");
        }
    };

    const env = await makeTestEnv({ serverData, mockRPC });

    try {
        await env.services.field.loadFields("take.five");
    } catch (error) {
        assert.strictEqual(error, "my little error");
    }
    try {
        await env.services.field.loadFields("take.five");
    } catch (error) {
        assert.strictEqual(error, "my little error");
    }

    assert.verifySteps(["fields_get", "fields_get"]);
});
