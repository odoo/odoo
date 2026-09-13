// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountWithSearch,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";

describe.current.tags("headless");

class TestComponent extends Component {
    static template = xml`<div class="o_test_component"/>`;
    static props = ["*"];
}

class Foo extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    bar = fields.Many2one({ relation: "partner" });
    properties = fields.Properties({
        definition_record: "bar",
        definition_record_field: "child_properties",
    });
    other_props = fields.Properties({
        definition_record: "bar",
        definition_record_field: "child_properties",
    });
    _records = [];
}

class Partner extends models.Model {
    name = fields.Char();
    child_properties = fields.PropertiesDefinition();
    _records = [];
}

defineModels([Foo, Partner]);

const ARCH = `
    <search>
        <field name="properties"/>
        <field name="other_props"/>
    </search>
`;

async function createSearchModel() {
    const component = await mountWithSearch(TestComponent, {
        resModel: "foo",
        searchViewId: false,
        searchViewArch: ARCH,
    });
    return component.env.searchModel;
}

function stubDefinitions(model, getDefinitions) {
    model._fetchPropertiesDefinition = async (_resModel, fieldName) => [
        {
            definitionRecordId: 1,
            definitionRecordName: "Parent",
            definitions: getDefinitions()[fieldName],
        },
    ];
}

async function activateAllPropertyGroupBys(model) {
    for (const item of model.getSearchItems((i) => i.isProperty)) {
        await model.toggleSearchItem(item.id);
    }
}

test("retiring one properties field leaves the other field's group-bys alone", async () => {
    const model = await createSearchModel();
    let definitions = {
        properties: [{ name: "p1", string: "P1", type: "char" }],
        other_props: [{ name: "q1", string: "Q1", type: "char" }],
    };
    stubDefinitions(model, () => definitions);

    await model.updateSearchViewItemsProperty();
    await activateAllPropertyGroupBys(model);
    expect(model.groupBy).toEqual(["properties.p1", "other_props.q1"]);

    definitions = { properties: [], other_props: definitions.other_props };
    await model.updateSearchViewItemsProperty();

    expect(model.groupBy).toEqual(["other_props.q1"]);
});

test("overlapping fills that both retire everything still settle", async () => {
    const model = await createSearchModel();
    let definitions = {
        properties: [{ name: "p1", string: "P1", type: "char" }],
        other_props: [{ name: "q1", string: "Q1", type: "char" }],
    };
    stubDefinitions(model, () => definitions);

    await model.updateSearchViewItemsProperty();
    await activateAllPropertyGroupBys(model);
    expect(model.groupBy).toHaveLength(2);

    definitions = { properties: [], other_props: [] };
    await Promise.all([
        model.updateSearchViewItemsProperty(),
        model.updateSearchViewItemsProperty(),
    ]);

    expect(model.groupBy).toEqual([]);
    expect(model.query).toEqual([]);
});

test("retiring a property also retires its synthesised field metadata", async () => {
    const model = await createSearchModel();
    let definitions = {
        properties: [{ name: "p1", string: "P1", type: "char" }],
        other_props: [{ name: "q1", string: "Q1", type: "char" }],
    };
    stubDefinitions(model, () => definitions);

    await model.updateSearchViewItemsProperty();
    expect(model.searchViewFields["properties.p1"]).not.toBe(undefined);
    expect(model.searchViewFields["other_props.q1"]).not.toBe(undefined);

    definitions = { properties: [], other_props: definitions.other_props };
    await model.updateSearchViewItemsProperty();

    expect(model.searchViewFields["properties.p1"]).toBe(undefined);
    expect(model.searchViewFields["other_props.q1"]).not.toBe(undefined);
});

test("a property whose definition record has no name is described the same on every expansion", async () => {
    const model = await createSearchModel();
    model._fetchPropertiesDefinition = async () => [
        {
            definitionRecordId: 1,
            definitionRecordName: /** @type {string | undefined} */ (undefined),
            definitions: [{ name: "p1", string: "P1", type: "char" }],
        },
    ];
    const [propertiesItem] = model.getSearchItems(
        (/** @type {any} */ item) => item.fieldName === "properties",
    );

    const first = await model.getSearchItemsProperties(propertiesItem);
    const second = await model.getSearchItemsProperties(propertiesItem);

    expect(first.map((/** @type {any} */ item) => item.description)).toEqual(["P1"]);
    expect(second.map((/** @type {any} */ item) => item.description)).toEqual(["P1"]);
    expect(second[0].id).toBe(first[0].id);
});

test("a retired property that was in the query drops out of it, and one that was not is silent", async () => {
    const model = await createSearchModel();
    let definitions = [
        { name: "p1", string: "P1", type: "char" },
        { name: "p2", string: "P2", type: "char" },
    ];
    model._fetchPropertiesDefinition = async () => [
        { definitionRecordId: 1, definitionRecordName: "Parent", definitions },
    ];
    const [propertiesItem] = model.getSearchItems(
        (/** @type {any} */ item) => item.fieldName === "properties",
    );
    const [p1, p2] = await model.getSearchItemsProperties(propertiesItem);
    await model.addAutoCompletionValues(p1.id, {
        label: "x",
        value: "x",
        operator: "ilike",
    });
    expect(model.query.map((/** @type {any} */ q) => q.searchItemId)).toEqual([p1.id]);

    definitions = [definitions[0]];
    expect(model._forgetSearchItems([p2.id])).toBe(false);
    expect(model.searchItems[p2.id]).toBe(undefined);

    definitions = [];
    await model.getSearchItemsProperties(propertiesItem);
    expect(model.searchItems[p1.id]).toBe(undefined);
    expect(model.query).toEqual([]);
});

test("a failing definitions fetch retires nothing", async () => {
    const model = await createSearchModel();
    const definitions = {
        properties: [{ name: "p1", string: "P1", type: "char" }],
        other_props: [],
    };
    stubDefinitions(model, () => definitions);

    await model.updateSearchViewItemsProperty();
    await activateAllPropertyGroupBys(model);
    expect(model.groupBy).toEqual(["properties.p1"]);

    model._fetchPropertiesDefinition = async () => {
        throw new Error("rpc down");
    };
    await model.updateSearchViewItemsProperty().catch(() => {});

    expect(model.groupBy).toEqual(["properties.p1"]);
});

test("refreshing property definitions updates group labels while preserving active ids", async () => {
    const model = await createSearchModel();
    let definitions = {
        properties: [{ name: "p1", string: "Old label", type: "char" }],
        other_props: [],
    };
    stubDefinitions(model, () => definitions);
    await model.updateSearchViewItemsProperty();
    const [before] = model.getSearchItems((item) => item.isProperty);
    await model.toggleSearchItem(before.id);
    definitions = {
        properties: [{ name: "p1", string: "New label", type: "char" }],
        other_props: [],
    };
    await model.updateSearchViewItemsProperty();
    const [after] = model.getSearchItems((item) => item.isProperty);
    expect(after.id).toBe(before.id);
    expect(after.description).toBe("New label");
    expect(after.isActive).toBe(true);
    expect(model.facets[0].values).toEqual(["New label"]);
});

test("refreshing a property search field replaces its selection metadata", async () => {
    const model = await createSearchModel();
    let definition = {
        name: "p1",
        string: "Status",
        type: "selection",
        selection: [["a", "Old"]],
    };
    model._fetchPropertiesDefinition = async () => [
        {
            definitionRecordId: 1,
            definitionRecordName: "Parent",
            definitions: [definition],
        },
    ];
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const [before] = await model.getSearchItemsProperties(parent);
    definition = {
        ...definition,
        selection: [
            ["a", "New"],
            ["b", "Added"],
        ],
    };
    const [after] = await model.getSearchItemsProperties(parent);
    expect(after.id).toBe(before.id);
    expect(after.propertyFieldDefinition.selection).toEqual(definition.selection);
});

test("refreshing an active property label invalidates an already read facet", async () => {
    const model = await createSearchModel();
    let definition = { name: "p1", string: "Old", type: "char" };
    model._fetchPropertiesDefinition = async () => [
        {
            definitionRecordId: 1,
            definitionRecordName: "Parent",
            definitions: [definition],
        },
    ];
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const [item] = await model.getSearchItemsProperties(parent);
    await model.addAutoCompletionValues(item.id, {
        label: "x",
        value: "x",
        operator: "ilike",
    });
    const previousDomain = model.domain;
    expect(model.facets[0].title).toBe("Old (Parent)");
    definition = { ...definition, string: "New" };
    await model.getSearchItemsProperties(parent);
    makeLogger("web.search.challenge").logic("active-property-facet", () => ({
        facet: model.facets[0],
        item: model.searchItems[item.id],
    }));
    expect(model.facets[0].title).toBe("New (Parent)");
    expect(model.domain).toEqual(previousDomain);
    expect(model.query[0].searchItemId).toBe(item.id);
});

test("property label refresh notifies presentation without reloading panel sections", async () => {
    const model = await createSearchModel();
    let definitions = {
        properties: [{ name: "p1", string: "Old", type: "char" }],
        other_props: [],
    };
    stubDefinitions(model, () => definitions);
    await model.updateSearchViewItemsProperty();
    const [item] = model.getSearchItems((item) => item.isProperty);
    await model.toggleSearchItem(item.id);
    expect(model.facets[0].values).toEqual(["Old"]);
    let reloads = 0;
    model._reloadSections = async () => {
        reloads++;
    };
    definitions = {
        ...definitions,
        properties: [{ name: "p1", string: "New", type: "char" }],
    };
    await model.updateSearchViewItemsProperty();
    expect(model.facets[0].values).toEqual(["New"]);
    expect(reloads).toBe(0);
});

test("moving a property name to another definition record does not reuse its old domain", async () => {
    const model = await createSearchModel();
    let recordId = 1;
    model._fetchPropertiesDefinition = async () => [
        {
            definitionRecordId: recordId,
            definitionRecordName: "Parent",
            definitions: [{ name: "p1", string: "P1", type: "char" }],
        },
    ];
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const [before] = await model.getSearchItemsProperties(parent);
    await model.addAutoCompletionValues(before.id, {
        label: "x",
        value: "x",
        operator: "ilike",
    });
    recordId = 2;
    const [after] = await model.getSearchItemsProperties(parent);
    makeLogger("web.search.improve").logic("property-record-transition", () => ({
        before,
        after,
        query: model.query,
    }));
    expect(after.id).not.toBe(before.id);
    expect(model.query).toEqual([]);
    await model.addAutoCompletionValues(after.id, {
        label: "y",
        value: "y",
        operator: "ilike",
    });
    expect(model.domain).toEqual([
        "&",
        ["bar", "=", 2],
        ["properties.p1", "ilike", "y"],
    ]);
});

for (const change of ["type", "comodel"]) {
    test(`incompatible property ${change} retires its old query and grouping`, async () => {
        const model = await createSearchModel();
        let definition = {
            name: "p1",
            string: "P1",
            type: "many2many",
            comodel: "partner",
        };
        stubDefinitions(model, () => ({ properties: [definition], other_props: [] }));
        const [parent] = model.getSearchItems(
            (item) => item.fieldName === "properties",
        );
        const [before] = await model.getSearchItemsProperties(parent);
        await model.addAutoCompletionValues(before.id, {
            label: "Partner",
            value: 1,
            operator: "in",
        });
        await model.updateSearchViewItemsProperty();
        const [group] = model.getSearchItems((item) => item.isProperty);
        await model.toggleSearchItem(group.id);
        definition =
            change === "type"
                ? { ...definition, type: "char", comodel: undefined }
                : { ...definition, comodel: "foo" };
        const [after] = await model.getSearchItemsProperties(parent);
        await model.updateSearchViewItemsProperty();
        const [newGroup] = model.getSearchItems((item) => item.isProperty);
        makeLogger("web.search.improve").logic("property-schema-transition", () => ({
            change,
            query: model.query,
            group: newGroup,
        }));
        expect(after.id).not.toBe(before.id);
        expect(newGroup.id).not.toBe(group.id);
        expect(model.query).toEqual([]);
        expect(model.groupBy).toEqual([]);
        expect(after.operator).toBe(change === "type" ? undefined : "in");
        expect(newGroup.fieldType).toBe(definition.type);
    });
}

test("a date property changed to text no longer offers date intervals", async () => {
    const model = await createSearchModel();
    let definition = { name: "p1", string: "P1", type: "date" };
    stubDefinitions(model, () => ({ properties: [definition], other_props: [] }));
    await model.updateSearchViewItemsProperty();
    const [before] = model.getSearchItems((item) => item.isProperty);
    await model.toggleDateGroupBy(before.id, "month");
    definition = { ...definition, type: "char" };
    await model.updateSearchViewItemsProperty();
    const [after] = model.getSearchItems((item) => item.isProperty);
    expect(after.type).toBe("groupBy");
    expect(after.options).toBe(undefined);
    expect(model.groupBy).toEqual([]);
    await model.toggleSearchItem(after.id);
    expect(model.groupBy).toEqual(["properties.p1"]);
});

test("property refresh propagates a required panel reload failure to its caller", async () => {
    const model = await createSearchModel();
    let definitions = [{ name: "p1", string: "P1", type: "char" }];
    model._fetchPropertiesDefinition = async () => [
        { definitionRecordId: 1, definitionRecordName: "Parent", definitions },
    ];
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const [item] = await model.getSearchItemsProperties(parent);
    await model.addAutoCompletionValues(item.id, {
        label: "x",
        value: "x",
        operator: "ilike",
    });
    definitions = [];
    model._reloadSections = async () => {
        throw new Error("panel reload failed");
    };
    await expect(model.getSearchItemsProperties(parent)).rejects.toThrow(
        "panel reload failed",
    );
    expect(model.query).toEqual([]);
});

function serveCollidingDefinitions(secondType = "char") {
    onRpc("partner", "web_search_read", () => ({
        length: 2,
        records: [
            {
                id: 1,
                display_name: "First",
                child_properties: [{ name: "shared", string: "Alpha", type: "char" }],
            },
            {
                id: 2,
                display_name: "Second",
                child_properties: [
                    { name: "shared", string: "Beta", type: secondType },
                ],
            },
        ],
    }));
}

test("the field service preserves same-named properties from distinct records for search", async () => {
    serveCollidingDefinitions();
    const model = await createSearchModel();
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const first = await model.getSearchItemsProperties(parent);
    makeLogger("web.search.continue").logic("colliding-definitions", () => ({
        items: first,
    }));
    expect(first.map((item) => item.description)).toEqual([
        "Alpha (First)",
        "Beta (Second)",
    ]);
    const again = await model.getSearchItemsProperties(parent);
    expect(again.map((item) => item.id)).toEqual(first.map((item) => item.id));
    for (const [index, item] of again.entries()) {
        await model.clearQuery();
        await model.addAutoCompletionValues(item.id, {
            label: "x",
            value: "x",
            operator: "ilike",
        });
        expect(model.domain).toEqual([
            "&",
            ["bar", "=", index + 1],
            ["properties.shared", "ilike", "x"],
        ]);
    }
});

test("compatible shared property names produce one stable group-by per field", async () => {
    serveCollidingDefinitions();
    const model = await createSearchModel();
    await model.updateSearchViewItemsProperty();
    const first = model.getSearchItems((item) => item.isProperty);
    expect(first.map((item) => item.fieldName)).toEqual([
        "properties.shared",
        "other_props.shared",
    ]);
    await model.updateSearchViewItemsProperty();
    expect(
        model.getSearchItems((item) => item.isProperty).map((item) => item.id),
    ).toEqual(first.map((item) => item.id));
});

test("incompatible shared property names remain searchable but do not offer an ambiguous group-by", async () => {
    serveCollidingDefinitions("date");
    const model = await createSearchModel();
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    expect(await model.getSearchItemsProperties(parent)).toHaveLength(2);
    await model.updateSearchViewItemsProperty();
    expect(model.getSearchItems((item) => item.isProperty)).toEqual([]);
    expect(model.searchViewFields["properties.shared"]).toBe(undefined);
});

for (const staleFailure of [false, true]) {
    test(`an older property response cannot replace a newer refresh (${staleFailure ? "failure" : "success"})`, async () => {
        const model = await createSearchModel();
        const [parent] = model.getSearchItems(
            (item) => item.fieldName === "properties",
        );
        const older = new Deferred();
        let calls = 0;
        model._fetchPropertiesDefinition = () =>
            ++calls === 1
                ? older
                : Promise.resolve([
                      {
                          definitionRecordId: 1,
                          definitionRecordName: "Parent",
                          definitions: [{ name: "p1", string: "New", type: "char" }],
                      },
                  ]);
        const pending = model.getSearchItemsProperties(parent);
        const [current] = await model.getSearchItemsProperties(parent);
        await model.addAutoCompletionValues(current.id, {
            label: "x",
            value: "x",
            operator: "ilike",
        });
        if (staleFailure) {
            older.reject(new Error("obsolete definition failure"));
        } else {
            older.resolve([
                {
                    definitionRecordId: 1,
                    definitionRecordName: "Parent",
                    definitions: [],
                },
            ]);
        }
        await pending;
        expect(model.searchItems[current.id].description).toBe("New (Parent)");
        expect(model.query[0].searchItemId).toBe(current.id);
    });
}

for (const staleFailure of [false, true]) {
    test(`switching active record starts a fresh group-definition request (${staleFailure ? "failure" : "success"})`, async () => {
        const model = await createSearchModel();
        const older = new Deferred();
        let calls = 0;
        model._fetchPropertiesDefinition = (_resModel, fieldName) => {
            if (fieldName !== "properties") {
                return Promise.resolve([]);
            }
            return ++calls === 1
                ? older
                : Promise.resolve([
                      {
                          definitionRecordId: 2,
                          definitionRecordName: "Second",
                          definitions: [
                              { name: "p2", string: "Current", type: "char" },
                          ],
                      },
                  ]);
        };
        const pending = model.updateSearchViewItemsProperty();
        await model.reload({ context: { active_id: 2 } });
        await model.updateSearchViewItemsProperty();
        expect(calls).toBe(2);
        if (staleFailure) {
            older.reject(new Error("obsolete group definitions"));
        } else {
            older.resolve([]);
        }
        await pending;
        expect(
            model
                .getSearchItems((item) => item.isProperty)
                .map((item) => item.fieldName),
        ).toEqual(["properties.p2"]);
    });
}

test("a property response for a previous active record does not add old filters", async () => {
    const model = await createSearchModel();
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const older = new Deferred();
    model._fetchPropertiesDefinition = () => older;
    const pending = model.getSearchItemsProperties(parent);
    await model.reload({ context: { active_id: 2 } });
    older.resolve([
        {
            definitionRecordId: 1,
            definitionRecordName: "Old",
            definitions: [{ name: "p1", string: "Old", type: "char" }],
        },
    ]);
    expect(await pending).toEqual([]);
    expect(model.getSearchItems((item) => item.type === "field_property")).toEqual([]);
});

test("a pending property fetch cannot attach to a replacement search view", async () => {
    const model = await createSearchModel();
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const pendingDefinitions = new Deferred();
    model._fetchPropertiesDefinition = () => pendingDefinitions;
    const pending = model.getSearchItemsProperties(parent);
    await model.load({
        resModel: "foo",
        searchViewId: false,
        searchViewArch: `<search><field name="foo"/></search>`,
    });
    pendingDefinitions.resolve([
        {
            definitionRecordId: 1,
            definitionRecordName: "Old",
            definitions: [{ name: "p1", string: "Old", type: "char" }],
        },
    ]);
    expect(await pending).toEqual([]);
    expect(await model.getSearchItemsProperties(parent)).toEqual([]);
    expect(model.getSearchItems((item) => item.type === "field_property")).toEqual([]);
});

test("a newly ambiguous property retires its active group-by", async () => {
    const model = await createSearchModel();
    let definitions = [
        {
            definitionRecordId: 1,
            definitionRecordName: "First",
            definitions: [{ name: "p1", string: "First", type: "char" }],
        },
    ];
    model._fetchPropertiesDefinition = (_model, field) =>
        Promise.resolve(field === "properties" ? definitions : []);
    await model.updateSearchViewItemsProperty();
    const [group] = model.getSearchItems((item) => item.isProperty);
    await model.toggleSearchItem(group.id);
    definitions = [
        ...definitions,
        {
            definitionRecordId: 2,
            definitionRecordName: "Second",
            definitions: [{ name: "p1", string: "Second", type: "date" }],
        },
    ];
    await model.updateSearchViewItemsProperty();
    expect(model.groupBy).toEqual([]);
    expect(model.query).toEqual([]);
    expect(model.searchViewFields["properties.p1"]).toBe(undefined);
});

for (const type of ["selection", "tags"]) {
    for (const options of [[["b", "Second"]], [["a", "Different meaning"]]]) {
        test(`same-typed ${type} definitions with incompatible choices cannot group (${options[0][0]})`, async () => {
            const model = await createSearchModel();
            const optionKey = type === "selection" ? "selection" : "tags";
            model._fetchPropertiesDefinition = async (_model, field) =>
                field !== "properties"
                    ? []
                    : [
                          {
                              definitionRecordId: 1,
                              definitionRecordName: "First",
                              definitions: [
                                  {
                                      name: "p1",
                                      string: "P1",
                                      type,
                                      [optionKey]: [["a", "First"]],
                                  },
                              ],
                          },
                          {
                              definitionRecordId: 2,
                              definitionRecordName: "Second",
                              definitions: [
                                  {
                                      name: "p1",
                                      string: "P1",
                                      type,
                                      [optionKey]: options,
                                  },
                              ],
                          },
                      ];
            await model.updateSearchViewItemsProperty();
            expect(model.getSearchItems((item) => item.isProperty)).toEqual([]);
        });
    }
}

test("choice ordering alone does not make a shared property grouping ambiguous", async () => {
    const model = await createSearchModel();
    const options = [
        ["a", "Alpha"],
        ["b", "Beta"],
    ];
    model._fetchPropertiesDefinition = async (_model, field) =>
        field !== "properties"
            ? []
            : [
                  {
                      definitionRecordId: 1,
                      definitionRecordName: "First",
                      definitions: [
                          {
                              name: "p1",
                              string: "P1",
                              type: "selection",
                              selection: options,
                          },
                      ],
                  },
                  {
                      definitionRecordId: 2,
                      definitionRecordName: "Second",
                      definitions: [
                          {
                              name: "p1",
                              string: "P1",
                              type: "selection",
                              selection: [...options].reverse(),
                          },
                      ],
                  },
              ];
    await model.updateSearchViewItemsProperty();
    expect(model.getSearchItems((item) => item.isProperty)).toHaveLength(1);
});

for (const type of ["selection", "tags"]) {
    test(`refreshing active ${type} choices refreshes facet values without changing the domain`, async () => {
        const model = await createSearchModel();
        const [parent] = model.getSearchItems(
            (item) => item.fieldName === "properties",
        );
        const optionKey = type === "selection" ? "selection" : "tags";
        let definition = {
            name: "p1",
            string: "Status",
            type,
            [optionKey]: [["a", "Old"]],
        };
        model._fetchPropertiesDefinition = async () => [
            {
                definitionRecordId: 1,
                definitionRecordName: "Parent",
                definitions: [definition],
            },
        ];
        const [item] = await model.getSearchItemsProperties(parent);
        await model.addAutoCompletionValues(item.id, {
            label: "Old",
            value: "a",
            operator: type === "tags" ? "in" : "=",
        });
        const domain = model.domain;
        expect(model.facets[0].values).toEqual(["Old"]);
        definition = { ...definition, [optionKey]: [["a", "New"]] };
        await model.getSearchItemsProperties(parent);
        makeLogger("web.search.correctness").logic("active-choice-refresh", () => ({
            type,
            facets: model.facets,
        }));
        expect(model.facets[0].values).toEqual(["New"]);
        expect(model.domain).toEqual(domain);
        expect(model.query[0].searchItemId).toBe(item.id);
        definition = { ...definition, [optionKey]: [] };
        await model.getSearchItemsProperties(parent);
        expect(model.facets[0].values).toEqual(["New"]);
        expect(model.domain).toEqual(domain);
        expect(model.query[0].searchItemId).toBe(item.id);
    });
}

test("replacing property field metadata starts a new group fill instead of sharing the obsolete fill", async () => {
    const model = await createSearchModel();
    const older = new Deferred();
    let calls = 0;
    model._fetchPropertiesDefinition = async (_model, field) =>
        field !== "properties"
            ? []
            : ++calls === 1
              ? older
              : [
                    {
                        definitionRecordId: 1,
                        definitionRecordName: "Current",
                        definitions: [{ name: "p2", string: "New", type: "char" }],
                    },
                ];
    const pending = model.updateSearchViewItemsProperty();
    model.searchViewFields.properties = { ...model.searchViewFields.properties };
    const current = model.updateSearchViewItemsProperty();
    expect(calls).toBe(2);
    older.resolve([]);
    await Promise.all([pending, current]);
    expect(
        model.getSearchItems((item) => item.isProperty).map((item) => item.fieldName),
    ).toEqual(["properties.p2"]);
});

test("a property search response for replaced field metadata is discarded", async () => {
    const model = await createSearchModel();
    const [parent] = model.getSearchItems((item) => item.fieldName === "properties");
    const older = new Deferred();
    model._fetchPropertiesDefinition = () => older;
    const pending = model.getSearchItemsProperties(parent);
    model.searchViewFields.properties = { ...model.searchViewFields.properties };
    older.resolve([
        {
            definitionRecordId: 1,
            definitionRecordName: "Old",
            definitions: [{ name: "p1", string: "Old", type: "char" }],
        },
    ]);
    expect(await pending).toEqual([]);
    expect(model.getSearchItems((item) => item.type === "field_property")).toEqual([]);
});
