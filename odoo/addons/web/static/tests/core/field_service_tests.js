/** @odoo-module **/

import { fieldService } from "@web/core/field_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getFixture, makeDeferred, mount, nextTick } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

function getModelInfo(resModel) {
    return {
        resModel,
        fieldDefs: serverData.models[resModel].fields,
    };
}

function getDefinitions() {
    const records = serverData.models.species.records;
    const fieldDefs = {};
    for (const record of records) {
        for (const definition of record.definitions) {
            fieldDefs[definition.name] = {
                is_property: true,
                searchable: true,
                record_name: record.display_name,
                record_id: record.id,
                ...definition,
            };
        }
    }
    return { resModel: "*", fieldDefs };
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
                        species: { type: "many2one", string: "Species", relation: "species" },
                        property_field: {
                            string: "Properties",
                            type: "properties",
                            definition_record: "species",
                            definition_record_field: "definitions",
                        },
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
                species: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        definitions: { string: "Definitions", type: "properties_definition" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "Galápagos tortoise",
                            definitions: [
                                {
                                    name: "galapagos_lifespans",
                                    string: "Lifespans",
                                    type: "integer",
                                },
                                {
                                    name: "location_ids",
                                    string: "Locations",
                                    type: "many2many",
                                    relation: "location",
                                },
                            ],
                        },
                        {
                            id: 2,
                            display_name: "Aldabra giant tortoise",
                            definitions: [
                                { name: "aldabra_lifespans", string: "Lifespans", type: "integer" },
                                { name: "color", string: "Color", type: "char" },
                            ],
                        },
                    ],
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
        {
            resModel: "tortoise",
            path: "property_field",
            expectedResult: {
                names: ["property_field"],
                modelsInfo: [getModelInfo("tortoise")],
            },
        },
        {
            resModel: "tortoise",
            path: "property_field.galapagos_lifespans",
            expectedResult: {
                names: ["property_field", "galapagos_lifespans"],
                modelsInfo: [getModelInfo("tortoise"), getDefinitions()],
            },
        },
        {
            resModel: "tortoise",
            path: "property_field.location_ids.tortoise_ids",
            expectedResult: {
                isInvalid: "path",
                names: ["property_field", "location_ids", "tortoise_ids"],
                modelsInfo: [getModelInfo("tortoise"), getDefinitions()],
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

QUnit.test("async method loadFields is protected", async (assert) => {
    assert.expect(7);

    let callFieldService;
    class Child extends Component {
        static template = xml`
            <div class="o_child_component" />
        `;
        setup() {
            this.fieldService = useService("field");
            callFieldService = async () => {
                assert.step("loadFields called");
                await this.fieldService.loadFields("tortoise");
                assert.step("loadFields result get");
            };
        }
    }

    class Parent extends Component {
        static components = { Child };
        static template = xml`
            <t t-if="state.displayChild">
                <Child />
            </t>
        `;
        setup() {
            this.state = useState({ displayChild: true });
        }
    }

    const target = getFixture();
    const def = makeDeferred();
    const env = await makeTestEnv({
        serverData,
        async mockRPC() {
            await def;
        },
    });
    const parent = await mount(Parent, target, { env });

    assert.containsOnce(target, ".o_child_component");

    callFieldService();
    assert.verifySteps(["loadFields called"]);

    parent.state.displayChild = false;
    await nextTick();

    def.resolve();
    await nextTick();

    assert.verifySteps([]);

    try {
        await callFieldService();
    } catch (e) {
        assert.step(e.message);
    }

    assert.verifySteps(["loadFields called", "Component is destroyed"]);
});
