import { expect, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    getService,
    makeMockEnv,
    MockServer,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function getModelInfo(resModel) {
    return {
        resModel: resModel._name,
        fieldDefs: JSON.parse(JSON.stringify(resModel._fields)),
    };
}

function getDefinitions() {
    const fieldDefs = {};
    for (const record of MockServer.env["species"]) {
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

class Tortoise extends models.Model {
    name = fields.Char();
    age = fields.Integer();
    location_id = fields.Many2one({ string: "Location", relation: "location" });
    species = fields.Many2one({ relation: "species" });
    property_field = fields.Properties({
        string: "Properties",
        definition_record: "species",
        definition_record_field: "definitions",
    });
}

class Location extends models.Model {
    name = fields.Char();
    tortoise_ids = fields.One2many({ string: "Turtles", relation: "tortoise" });
}

class Species extends models.Model {
    name = fields.Char();
    definitions = fields.PropertiesDefinition();

    _records = [
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
    ];
}

defineModels([Tortoise, Location, Species]);

test("loadPath", async () => {
    await makeMockEnv();

    const toTest = [
        {
            resModel: "tortoise",
            path: "*",
            expectedResult: {
                names: ["*"],
                modelsInfo: [getModelInfo(Tortoise)],
            },
        },
        {
            resModel: "tortoise",
            path: "*.a",
            expectedResult: {
                isInvalid: "path",
                names: ["*", "a"],
                modelsInfo: [getModelInfo(Tortoise)],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.*",
            expectedResult: {
                names: ["location_id", "*"],
                modelsInfo: [getModelInfo(Tortoise), getModelInfo(Location)],
            },
        },
        {
            resModel: "tortoise",
            path: "age",
            expectedResult: {
                names: ["age"],
                modelsInfo: [getModelInfo(Tortoise)],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id",
            expectedResult: {
                names: ["location_id"],
                modelsInfo: [getModelInfo(Tortoise)],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.tortoise_ids",
            expectedResult: {
                names: ["location_id", "tortoise_ids"],
                modelsInfo: [getModelInfo(Tortoise), getModelInfo(Location)],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.tortoise_ids.age",
            expectedResult: {
                names: ["location_id", "tortoise_ids", "age"],
                modelsInfo: [
                    getModelInfo(Tortoise),
                    getModelInfo(Location),
                    getModelInfo(Tortoise),
                ],
            },
        },
        {
            resModel: "tortoise",
            path: "location_id.tortoise_ids.age",
            expectedResult: {
                names: ["location_id", "tortoise_ids", "age"],
                modelsInfo: [
                    getModelInfo(Tortoise),
                    getModelInfo(Location),
                    getModelInfo(Tortoise),
                ],
            },
        },
        {
            resModel: "tortoise",
            path: "property_field",
            expectedResult: {
                names: ["property_field"],
                modelsInfo: [getModelInfo(Tortoise)],
            },
        },
        {
            resModel: "tortoise",
            path: "property_field.galapagos_lifespans",
            expectedResult: {
                names: ["property_field", "galapagos_lifespans"],
                modelsInfo: [getModelInfo(Tortoise), getDefinitions()],
            },
        },
        {
            resModel: "tortoise",
            path: "property_field.location_ids.tortoise_ids",
            expectedResult: {
                isInvalid: "path",
                names: ["property_field", "location_ids", "tortoise_ids"],
                modelsInfo: [getModelInfo(Tortoise), getDefinitions()],
            },
        },
    ];
    for (const { resModel, path, expectedResult } of toTest) {
        const result = await getService("field").loadPath(resModel, path);
        expect(result).toEqual(expectedResult);
    }

    const errorToTest = [
        { resModel: "notAModel" },
        { resModel: "tortoise", path: {} },
        { resModel: "tortoise", path: "" },
    ];

    for (const { resModel, path } of errorToTest) {
        try {
            await getService("field").loadPath(resModel, path);
        } catch {
            expect.step("error");
        }
    }
    expect.verifySteps(errorToTest.map(() => "error"));
});

test("store loadFields calls in cache in success", async () => {
    onRpc("fields_get", () => {
        expect.step("fields_get");
    });

    await makeMockEnv();

    await getService("field").loadFields("tortoise");
    await getService("field").loadFields("tortoise");

    expect.verifySteps(["fields_get"]);
});

test("does not store loadFields calls in cache when failed", async () => {
    onRpc("fields_get", () => {
        expect.step("fields_get");
        throw "my little error";
    });

    await makeMockEnv();
    await expect(getService("field").loadFields("take.five")).rejects.toThrow(/my little error/);
    await expect(getService("field").loadFields("take.five")).rejects.toThrow(/my little error/);

    expect.verifySteps(["fields_get", "fields_get"]);
});

test("async method loadFields is protected", async () => {
    let callFieldService;
    class Child extends Component {
        static template = xml`
            <div class="o_child_component" />
        `;
        static props = ["*"];
        setup() {
            this.fieldService = useService("field");
            callFieldService = async () => {
                expect.step("loadFields called");
                await this.fieldService.loadFields("tortoise");
                expect.step("loadFields result get");
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
        static props = ["*"];
        setup() {
            this.state = useState({ displayChild: true });
        }
    }

    const def = new Deferred();
    onRpc(async () => {
        await def;
    });
    const parent = await mountWithCleanup(Parent);

    expect(".o_child_component").toHaveCount(1);

    callFieldService();
    expect.verifySteps(["loadFields called"]);

    parent.state.displayChild = false;
    await animationFrame();

    def.resolve();
    await animationFrame();

    expect.verifySteps([]);

    try {
        await callFieldService();
    } catch (e) {
        expect.step(e.message);
    }

    expect.verifySteps(["loadFields called", "Component is destroyed"]);
});
