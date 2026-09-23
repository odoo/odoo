// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    getService,
    makeMockEnv,
    MockServer,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { useService, useServiceProtectMethodHandling } from "@web/core/utils/hooks";

/** @param {typeof models.Model} resModel */
function getModelInfo(resModel) {
    return {
        resModel: resModel._name,
        fieldDefs: JSON.parse(JSON.stringify(resModel._fields)),
    };
}

/** @param {string} [resModel] */
function getDefinitions(resModel) {
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
    return { resModel: resModel || "*", fieldDefs };
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
            await getService("field").loadPath(resModel, /** @type {any} */ (path));
        } catch {
            expect.step("error");
        }
    }
    expect.verifySteps(errorToTest.map(() => "error"));
});

test("loadPath follow relational properties", async () => {
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
                modelsInfo: [getModelInfo(Tortoise), getDefinitions("tortoise")],
            },
        },
        {
            resModel: "tortoise",
            path: "property_field.location_ids.tortoise_ids",
            expectedResult: {
                names: ["property_field", "location_ids", "tortoise_ids"],
                modelsInfo: [
                    getModelInfo(Tortoise),
                    getDefinitions("tortoise"),
                    getModelInfo(Location),
                ],
            },
        },
    ];
    for (const { resModel, path, expectedResult } of toTest) {
        const result = await getService("field").loadPath(resModel, path, true);
        expect(result).toEqual(expectedResult);
    }

    const errorToTest = [
        { resModel: "notAModel" },
        { resModel: "tortoise", path: {} },
        { resModel: "tortoise", path: "" },
    ];

    for (const { resModel, path } of errorToTest) {
        try {
            await getService("field").loadPath(
                resModel,
                /** @type {any} */ (path),
                true,
            );
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

test("loadFields returns a mutable top-level object per call", async () => {
    await makeMockEnv();

    const a = await getService("field").loadFields("tortoise");
    const b = await getService("field").loadFields("tortoise");
    expect(a).not.toBe(b);
    a["property.custom"] = { type: "char", name: "property.custom" };
    expect(a["property.custom"].name).toBe("property.custom");
    expect(b["property.custom"]).toBe(undefined);
});

test("does not store loadFields calls in cache when failed", async () => {
    onRpc("fields_get", () => {
        expect.step("fields_get");
        throw "my little error";
    });

    await makeMockEnv();
    await expect(getService("field").loadFields("take.five")).rejects.toThrow(
        /my little error/,
    );
    await expect(getService("field").loadFields("take.five")).rejects.toThrow(
        /my little error/,
    );

    expect.verifySteps(["fields_get", "fields_get"]);
});

test("async method loadFields is protected", async () => {
    patchWithCleanup(useServiceProtectMethodHandling, {
        fn: useServiceProtectMethodHandling.original,
    });
    /** @type {() => Promise<void>} */
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
            <t t-if="this.state.displayChild">
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

test("followRelationalProperties survives a relational hop", async () => {
    await makeMockEnv();
    const field = getService("field");

    const direct = await field.loadPath(
        "tortoise",
        "property_field.location_ids.name",
        true,
    );
    expect(direct.isInvalid).toBe(undefined);
    expect(direct.modelsInfo.map((m) => m.resModel)).toEqual([
        "tortoise",
        "tortoise",
        "location",
    ]);

    const hopped = await field.loadPath(
        "tortoise",
        "location_id.tortoise_ids.property_field.location_ids.name",
        true,
    );
    expect(hopped.isInvalid).toBe(undefined);
    expect(hopped.modelsInfo.map((m) => m.resModel)).toEqual([
        "tortoise",
        "location",
        "tortoise",
        "tortoise",
        "location",
    ]);
});

test("loadPath rejects an invalid path before issuing any RPC", async () => {
    await makeMockEnv();
    onRpc("tortoise", "fields_get", () => expect.step("fields_get"));
    await expect(getService("field").loadPath("tortoise", "")).rejects.toThrow(
        /Invalid path/,
    );
    expect.verifySteps([]);
});

test("a properties field whose definition_record_field the server cannot serve fails by name", async () => {
    await makeMockEnv();
    onRpc("fields_get", () => ({
        my_props: {
            type: "properties",
            definition_record: "holder_id",
            definition_record_field: "custom_defs",
        },
        holder_id: { type: "many2one", relation: "properties.base.definition" },
    }));
    await expect(
        getService("field").loadPropertyDefinitions("holder", "my_props"),
    ).rejects.toThrow(
        /names "custom_defs" as its definition_record_field, but properties\.base\.definition only serves "properties_definition"/,
    );
});

test("the same field named properties_definition resolves normally", async () => {
    await makeMockEnv();
    onRpc("fields_get", () => ({
        my_props: {
            type: "properties",
            definition_record: "holder_id",
            definition_record_field: "properties_definition",
        },
        holder_id: { type: "many2one", relation: "properties.base.definition" },
    }));
    onRpc(
        "/web/dataset/call_kw/properties.base.definition/get_properties_base_definition",
        () => ({
            records: [
                {
                    id: 1,
                    display_name: "h",
                    properties_definition: [{ name: "p", type: "char" }],
                },
            ],
            length: 1,
        }),
    );
    const defs = await getService("field").loadPropertyDefinitions(
        "holder",
        "my_props",
    );
    expect(Object.keys(defs)).toEqual(["p"]);
});
