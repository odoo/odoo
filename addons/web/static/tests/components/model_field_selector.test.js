// @ts-check

import { expect, getFixture, test } from "@odoo/hoot";
import { press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    clickPrev,
    followRelation,
    getDisplayedFieldNames,
    getFocusedFieldName,
    getModelFieldSelectorValues,
    getTitle,
    openModelFieldSelectorPopover,
} from "@web/../tests/components/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { ModelFieldSelector } from "@web/components/model_field_selector/model_field_selector";

class Partner extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    product_id = fields.Many2one({ relation: "product" });
    json_field = fields.Json();

    _records = [
        { id: 1, foo: "yop", bar: true, product_id: 37 },
        { id: 2, foo: "blip", bar: true, product_id: false },
        { id: 4, foo: "abc", bar: false, product_id: 41 },
    ];
}

class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

defineModels([Partner, Product]);

function addProperties() {
    Partner._fields.properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
    });
    Product._fields.definitions = fields.PropertiesDefinition({
        string: "Definitions",
    });
    Product._records[0].definitions = [
        { name: "xphone_prop_1", string: "P1", type: "boolean" },
        { name: "xphone_prop_2", string: "P2", type: "char" },
    ];
    Product._records[1].definitions = [
        { name: "xpad_prop_1", string: "P1", type: "date" },
    ];
}

test("creating a field chain from scratch", async () => {
    const getValueFromDOM = (root) =>
        queryAllTexts(".o_model_field_selector_chain_part", { root }).join(" -> ");

    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                isDebugMode="false"
                update="(path) => this.onUpdate(path)"
            />
        `;
        static props = ["*"];
        setup() {
            this.path = "";
        }
        onUpdate(path) {
            expect.step(`update: ${path}`);
            this.path = path;
            this.render();
        }
    }

    const fieldSelector = await mountWithCleanup(Parent);

    await openModelFieldSelectorPopover();
    expect("input.o_input[placeholder='Search...']").toBeFocused();
    expect(".o_model_field_selector_popover").toHaveCount(1);

    expect(".o_model_field_selector_popover_item_name:first").toHaveText("Bar");

    await contains(".o_model_field_selector_popover_item_name").click();
    expect(".o_model_field_selector_popover").toHaveCount(0);
    expect(getValueFromDOM()).toBe("Bar");
    expect(fieldSelector.path).toBe("bar");
    expect.verifySteps(["update: bar"]);

    await openModelFieldSelectorPopover();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect(
        ".o_model_field_selector_popover .o_model_field_selector_popover_relation_icon",
    ).toHaveCount(1, {
        message: "field selector popover should contain the 'Product' field",
    });

    await followRelation();
    expect(".o_model_field_selector_popover_item_name").toHaveCount(5);
    expect(queryAllTexts(".o_model_field_selector_popover_item_name").at(-1)).toBe(
        "Product Name",
        {
            message: "the name of the last suggestion should be 'Product Name'",
        },
    );
    await contains(".o_model_field_selector_popover_item_name:last").click();
    expect(".o_model_field_selector_popover").toHaveCount(0);
    expect(getValueFromDOM()).toBe("Product -> Product Name");
    expect.verifySteps(["update: product_id.name"]);

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_prev_page").click();
    await contains(".o_model_field_selector_popover_close").click();
    expect.verifySteps(["update: product_id"]);

    await openModelFieldSelectorPopover();
    expect(
        ".o_model_field_selector_popover .o_model_field_selector_popover_relation_icon",
    ).toHaveCount(1);

    await followRelation();
    await contains(".o_model_field_selector_popover_item_name:last").click();
    expect(".o_model_field_selector_popover").toHaveCount(0);
    expect(getValueFromDOM()).toBe("Product -> Product Name");
    expect.verifySteps(["update: product_id.name"]);
});

test("default field chain should set the page data correctly", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "product_id",
            resModel: "partner",
            isDebugMode: false,
        },
    });
    await openModelFieldSelectorPopover();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect(getDisplayedFieldNames()).toEqual([
        "Bar",
        "Created on",
        "Display name",
        "Foo",
        "Id",
        "Last Modified on",
        "Product",
    ]);
    expect(".o_model_field_selector_popover_item:last").toHaveClass("active");
});

test("use the filter option", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "",
            resModel: "partner",
            filter: (field, path, resModel) => {
                const result = field.type === "many2one" && field.searchable;
                if (result) {
                    expect.step(resModel);
                }
                return result;
            },
        },
    });
    await openModelFieldSelectorPopover();
    expect(getDisplayedFieldNames()).toEqual(["Product"]);
    expect.verifySteps(["partner"]);
});

test("use the sort option", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "",
            resModel: "partner",
            sort: (fields) =>
                Object.keys(fields).sort((a, b) =>
                    fields[b].string.localeCompare(fields[a].string),
                ),
        },
    });
    await openModelFieldSelectorPopover();
    expect(getDisplayedFieldNames()).toEqual([
        "Product",
        "Last Modified on",
        "Id",
        "Foo",
        "Display name",
        "Created on",
        "Bar",
    ]);
});

test("default `showSearchInput` option", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "",
            resModel: "partner",
        },
    });
    await openModelFieldSelectorPopover();
    expect(
        ".o_model_field_selector_popover .o_model_field_selector_popover_search",
    ).toHaveCount(1);
    expect(getDisplayedFieldNames()).toEqual([
        "Bar",
        "Created on",
        "Display name",
        "Foo",
        "Id",
        "Last Modified on",
        "Product",
    ]);

    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
    ).edit("xx", { confirm: false });
    await runAllTimers();
    expect(getDisplayedFieldNames()).toBeEmpty();

    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
    ).edit("Pro", { confirm: false });
    await runAllTimers();
    expect(getDisplayedFieldNames()).toEqual(["Product"]);
});

test("false `showSearchInput` option", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            showSearchInput: false,
            path: "",
            resModel: "partner",
        },
    });
    await openModelFieldSelectorPopover();
    expect(
        ".o_model_field_selector_popover .o_model_field_selector_popover_search",
    ).toHaveCount(0);
});

test("create a field chain with value 1 i.e. TRUE_LEAF", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            showSearchInput: false,
            path: 1,
            resModel: "partner",
        },
    });
    expect(".o_model_field_selector_chain_part").toHaveText("1");
});

test("create a field chain with value 0 i.e. FALSE_LEAF", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            showSearchInput: false,
            path: 0,
            resModel: "partner",
        },
    });
    expect(".o_model_field_selector_chain_part").toHaveText("0", {
        message: "field name value should be 0.",
    });
});

test("cache fields_get", async () => {
    Partner._fields.partner_id = fields.Many2one({
        string: "Partner",
        relation: "partner",
    });

    onRpc("fields_get", ({ method }) => expect.step(method));

    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "partner_id.partner_id.partner_id.foo",
            resModel: "partner",
        },
    });
    expect.verifySteps(["fields_get"]);
});

test("Using back button in popover", async () => {
    Partner._fields.partner_id = fields.Many2one({
        string: "Partner",
        relation: "partner",
    });

    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                update="(path) => this.onUpdate(path)"
            />
        `;
        static props = ["*"];
        setup() {
            this.path = "partner_id.foo";
        }
        onUpdate(path) {
            this.path = path;
            this.render();
        }
    }

    await mountWithCleanup(Parent);
    expect(getModelFieldSelectorValues()).toEqual(["Partner", "Foo"]);
    expect(".o_model_field_selector i.o_model_field_selector_warning").toHaveCount(0);

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_prev_page").click();
    expect(getModelFieldSelectorValues()).toEqual(["Partner"]);
    expect(".o_model_field_selector i.o_model_field_selector_warning").toHaveCount(0);

    await contains(
        ".o_model_field_selector_popover_item:nth-child(1) .o_model_field_selector_popover_item_name",
    ).click();
    expect(getModelFieldSelectorValues()).toEqual(["Bar"]);
    expect(".o_model_field_selector_popover").toHaveCount(0);
});

test("select a relational field does not follow relation", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "",
            resModel: "partner",
            update(path) {
                expect.step(path);
            },
        },
    });
    await openModelFieldSelectorPopover();
    expect(
        ".o_model_field_selector_popover_item:last-child .o_model_field_selector_popover_relation_icon",
    ).toHaveCount(1);

    await contains(
        ".o_model_field_selector_popover_item:last-child .o_model_field_selector_popover_item_name",
    ).click();
    expect.verifySteps(["product_id"]);
    expect(".o_popover").toHaveCount(0);

    await openModelFieldSelectorPopover();
    expect(getDisplayedFieldNames()).toEqual([
        "Bar",
        "Created on",
        "Display name",
        "Foo",
        "Id",
        "Last Modified on",
        "Product",
    ]);
    expect(".o_model_field_selector_popover_relation_icon").toHaveCount(1);

    await followRelation();
    expect(getDisplayedFieldNames()).toEqual([
        "Created on",
        "Display name",
        "Id",
        "Last Modified on",
        "Product Name",
    ]);
    expect(".o_popover").toHaveCount(1);

    await contains(".o_model_field_selector_popover_item_name").click();
    expect.verifySteps(["product_id.create_date"]);
    expect(".o_popover").toHaveCount(0);
});

test("can follow relations", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "",
            resModel: "partner",
            followRelations: true,
            update(path) {
                expect(path).toBe("product_id");
            },
        },
    });
    await openModelFieldSelectorPopover();
    expect(getDisplayedFieldNames()).toEqual([
        "Bar",
        "Created on",
        "Display name",
        "Foo",
        "Id",
        "Last Modified on",
        "Product",
    ]);
    expect(".o_model_field_selector_popover_relation_icon").toHaveCount(1);

    await followRelation();
    expect(getDisplayedFieldNames()).toEqual([
        "Created on",
        "Display name",
        "Id",
        "Last Modified on",
        "Product Name",
    ]);
    expect(".o_popover").toHaveCount(1);
});

test("cannot follow relations", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "",
            resModel: "partner",
            followRelations: false,
            update(path) {
                expect(path).toBe("product_id");
            },
        },
    });
    await openModelFieldSelectorPopover();
    expect(getDisplayedFieldNames()).toEqual([
        "Bar",
        "Created on",
        "Display name",
        "Foo",
        "Id",
        "Last Modified on",
        "Product",
    ]);
    expect(".o_model_field_selector_popover_relation_icon").toHaveCount(0);
    await contains(".o_model_field_selector_popover_item_name:last").click();
    expect(".o_popover").toHaveCount(0);
    expect(getModelFieldSelectorValues()).toEqual(["Product"]);
});

test("Edit path in popover debug input", async () => {
    Partner._fields.partner_id = fields.Many2one({
        string: "Partner",
        relation: "partner",
    });

    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                isDebugMode="true"
                update="(pathInfo) => this.onUpdate(pathInfo)"
            />
        `;
        static props = ["*"];
        setup() {
            this.path = "foo";
        }
        onUpdate(path) {
            this.path = path;
            this.render();
        }
    }

    await mountWithCleanup(Parent);
    expect(getModelFieldSelectorValues()).toEqual(["Foo"]);

    await openModelFieldSelectorPopover();
    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_debug",
    ).edit("partner_id.bar");
    expect(getModelFieldSelectorValues()).toEqual(["Partner", "Bar"]);
});

test("title on first four pages", async () => {
    class Turtle extends models.Model {
        mother_id = fields.Many2one({
            string: "Mother",
            relation: "turtle",
        });
    }
    defineModels([Turtle]);

    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "mother_id",
            resModel: "turtle",
        },
    });
    await openModelFieldSelectorPopover();
    expect(getTitle()).toBe("Select a field");

    await followRelation();
    expect(getTitle()).toBe("Mother");

    await followRelation();
    expect(getTitle()).toBe("... > Mother");

    await followRelation();
    expect(getTitle()).toBe("... > Mother");
});

test("start on complex path and click prev", async () => {
    class Turtle extends models.Model {
        mother_id = fields.Many2one({
            string: "Mother",
            relation: "turtle",
        });
        father_id = fields.Many2one({
            string: "Father",
            relation: "turtle",
        });
    }
    defineModels([Turtle]);

    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "mother_id.father_id.mother_id",
            resModel: "turtle",
        },
    });

    await openModelFieldSelectorPopover();
    expect(getTitle()).toBe("... > Father");
    expect(getFocusedFieldName()).toBe("Mother");
    expect(getModelFieldSelectorValues()).toEqual(["Mother", "Father", "Mother"]);

    await followRelation();
    expect(getTitle()).toBe("... > Father");
    expect(getFocusedFieldName()).toBe("Created on");
    expect(getModelFieldSelectorValues()).toEqual(["Mother", "Father", "Father"]);

    await clickPrev();
    expect(getTitle()).toBe("... > Father");
    expect(getFocusedFieldName()).toBe("Father");
    expect(getModelFieldSelectorValues()).toEqual(["Mother", "Father", "Father"]);

    await clickPrev();
    expect(getTitle()).toBe("Mother");
    expect(getFocusedFieldName()).toBe("Father");
    expect(getModelFieldSelectorValues()).toEqual(["Mother", "Father"]);

    await clickPrev();
    expect(getTitle()).toBe("Select a field");
    expect(getFocusedFieldName()).toBe("Mother");
    expect(getModelFieldSelectorValues()).toEqual(["Mother"]);
    expect(".o_model_field_selector_popover_prev_page").toHaveCount(0);
});

test("support of invalid paths (allowEmpty=false)", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="state.path" />`;
        static props = ["*"];
        setup() {
            /** @type {{ path: unknown }} */
            this.state = useState({ path: `` });
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(getModelFieldSelectorValues()).toEqual(["-"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = undefined;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["-"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = false;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["-"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = {};
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["-"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = `a`;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["a"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = `foo.a`;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["Foo", "a"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = `a.foo`;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["a", "foo"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);
});

test("support of invalid paths (allowEmpty=true)", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="state.path" allowEmpty="true" />`;
        static props = ["*"];
        setup() {
            /** @type {{ path: unknown }} */
            this.state = useState({ path: `` });
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(getModelFieldSelectorValues()).toEqual([]);
    expect(".o_model_field_selector_warning").toHaveCount(0);

    parent.state.path = undefined;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual([]);
    expect(".o_model_field_selector_warning").toHaveCount(0);

    parent.state.path = false;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual([]);
    expect(".o_model_field_selector_warning").toHaveCount(0);

    parent.state.path = {};
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["-"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = `a`;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["a"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = `foo.a`;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["Foo", "a"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    parent.state.path = `a.foo`;
    await animationFrame();
    expect(getModelFieldSelectorValues()).toEqual(["a", "foo"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);
});

test("debug input", async () => {
    expect.assertions(10);
    let num = 1;
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" isDebugMode="true" path="state.path" update.bind="update"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ path: `` });
        }
        update(path, fieldInfo) {
            if (num === 1) {
                expect(path).toBe("a");
                expect(fieldInfo).toEqual({
                    fieldDef: null,
                    resModel: "partner",
                });
                num++;
            } else {
                expect(path).toBe("foo");
                expect(fieldInfo).toEqual({
                    resModel: "partner",
                    fieldDef: {
                        string: "Foo",
                        readonly: false,
                        required: false,
                        searchable: true,
                        sortable: true,
                        store: true,
                        groupable: true,
                        type: "char",
                        name: "foo",
                        trim: true,
                    },
                });
            }
        }
    }

    await mountWithCleanup(Parent);
    expect(getModelFieldSelectorValues()).toEqual(["-"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_debug").edit("a", { confirm: false });
    await contains(".o_model_field_selector_popover_search").click();
    expect(getModelFieldSelectorValues()).toEqual(["a"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);

    await contains(".o_model_field_selector_popover_close").click();

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_debug").edit("foo");
    expect(getModelFieldSelectorValues()).toEqual(["Foo"]);
    expect(".o_model_field_selector_warning").toHaveCount(0);

    await contains(".o_model_field_selector_popover_close").click();
});

test("focus on search input", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="state.path" update.bind="update"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ path: `foo` });
        }
        update() {}
    }

    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    expect(".o_model_field_selector_popover_search .o_input").toBeFocused();

    await followRelation();
    expect(".o_model_field_selector_popover_search .o_input").toBeFocused();
});

test("support properties", async () => {
    addProperties();

    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                isDebugMode="true"
                update="(path, fieldInfo) => this.onUpdate(path)"
            />
        `;
        static props = ["*"];
        setup() {
            this.path = "foo";
        }
        onUpdate(path) {
            this.path = path;
            expect.step(path);
            this.render();
        }
    }

    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    expect(getTitle()).toBe("Select a field");
    expect('.o_model_field_selector_popover_item[data-name="properties"]').toHaveCount(
        1,
    );
    expect(
        '.o_model_field_selector_popover_item[data-name="properties"] .o_model_field_selector_popover_relation_icon',
    ).toHaveCount(1);
    expect(getModelFieldSelectorValues()).toEqual(["Foo"]);
    expect(".o_model_field_selector_warning").toHaveCount(0);

    await contains(
        '.o_model_field_selector_popover_item[data-name="properties"] .o_model_field_selector_popover_relation_icon',
    ).click();
    expect(getModelFieldSelectorValues()).toEqual(["Properties"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);
    expect.verifySteps([]);

    await clickPrev();
    expect(getTitle()).toBe("Select a field");
    await contains(
        '.o_model_field_selector_popover_item[data-name="properties"] .o_model_field_selector_popover_item_name',
    ).click();
    expect(getTitle()).toBe("Properties");
    expect(".o_model_field_selector_value").toHaveText("Properties");
    expect(".o_model_field_selector_popover_item").toHaveCount(3);
    expect(
        '.o_model_field_selector_popover_item[data-name="xphone_prop_1"]',
    ).toHaveCount(1);
    expect(
        '.o_model_field_selector_popover_item[data-name="xphone_prop_2"]',
    ).toHaveCount(1);
    expect('.o_model_field_selector_popover_item[data-name="xpad_prop_1"]').toHaveCount(
        1,
    );
    expect(getDisplayedFieldNames()).toEqual([
        "P1 (xphone)\nxphone_prop_1 (boolean)",
        "P1 (xpad)\nxpad_prop_1 (date)",
        "P2 (xphone)\nxphone_prop_2 (char)",
    ]);

    await contains(
        '.o_model_field_selector_popover_item[data-name="xphone_prop_2"] .o_model_field_selector_popover_item_name',
    ).click();
    expect.verifySteps(["properties.xphone_prop_2"]);
    expect(".o_model_field_selector_value").toHaveText("PropertiesP2");
    expect(".o_model_field_selector_warning").toHaveCount(0);
});

test("search on field string and name in debug mode", async () => {
    Partner._fields.ucit = fields.Char({
        type: "char",
        string: "Some string",
    });
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="'foo'"
                isDebugMode="true"
            />
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
    ).edit("uct", { confirm: false });
    await runAllTimers();
    expect(getDisplayedFieldNames()).toEqual([
        "Product\nproduct_id (many2one)",
        "Some string\nucit (char)",
    ]);
});

test("clear button (allowEmpty=true)", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                allowEmpty="true"
                isDebugMode="true"
                update="(path, fieldInfo) => this.onUpdate(path)"
            />
        `;
        static props = ["*"];
        setup() {
            this.path = "baaarrr";
        }
        onUpdate(path) {
            this.path = path;
            expect.step(`path is ${JSON.stringify(path)}`);
            this.render();
        }
    }

    await mountWithCleanup(Parent);

    expect(getModelFieldSelectorValues()).toEqual(["baaarrr"]);
    expect(".o_model_field_selector_warning").toHaveCount(1);
    expect(".o_model_field_selector .fa-solid.fa-xmark").toHaveCount(1);

    await contains(".o_model_field_selector .fa-solid.fa-xmark").click();
    expect(getModelFieldSelectorValues()).toEqual([]);
    expect(".o_model_field_selector_warning").toHaveCount(0);
    expect(".o_model_field_selector .fa-solid.fa-xmark").toHaveCount(0);
    expect.verifySteps([`path is ""`]);

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name").click();
    expect(getModelFieldSelectorValues()).toEqual(["Bar"]);
    expect(".o_model_field_selector_warning").toHaveCount(0);
    expect(".o_model_field_selector .fa-solid.fa-xmark").toHaveCount(1);
    expect.verifySteps([`path is "bar"`]);

    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector .fa-solid.fa-xmark").click();
    expect(getModelFieldSelectorValues()).toEqual([]);
    expect(".o_model_field_selector_warning").toHaveCount(0);
    expect(".o_model_field_selector .fa-solid.fa-xmark").toHaveCount(0);
    expect.verifySteps([`path is ""`]);
});

test("Modify path in popover debug input and click away", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`
            <ModelFieldSelector
                readonly="false"
                resModel="'partner'"
                path="path"
                isDebugMode="true"
                update.bind="update"
            />
        `;
        static props = ["*"];
        setup() {
            this.path = "foo";
        }
        update(path) {
            this.path = path;
            expect.step(path);
            this.render();
        }
    }

    await mountWithCleanup(Parent);
    expect(getModelFieldSelectorValues()).toEqual(["Foo"]);

    await openModelFieldSelectorPopover();
    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_debug",
    ).edit("foooooo", { confirm: false });
    expect(getModelFieldSelectorValues()).toEqual(["Foo"]);

    await contains(getFixture()).click();
    expect(getModelFieldSelectorValues()).toEqual(["foooooo"]);
    expect.verifySteps(["foooooo"]);
});

test("showDebugInput = false", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "product_id",
            resModel: "partner",
            isDebugMode: true,
            showDebugInput: false,
        },
    });

    await openModelFieldSelectorPopover();
    expect(".o_model_field_selector_debug").toHaveCount(0);
});

test("debug input keydown does not navigate the search page", async () => {
    await mountWithCleanup(ModelFieldSelector, {
        props: {
            readonly: false,
            path: "product_id.name",
            resModel: "partner",
            isDebugMode: true,
            update: () => {},
        },
    });
    await openModelFieldSelectorPopover();
    expect(getTitle()).toBe("Product");
    const focusedBefore = getFocusedFieldName();

    const focusDebugAtStart = () => {
        const debugInput = /** @type {HTMLInputElement} */ (
            queryOne(".o_model_field_selector_debug")
        );
        debugInput.focus();
        debugInput.setSelectionRange(0, 0);
    };

    focusDebugAtStart();
    await press("ArrowUp");
    await animationFrame();
    expect(getFocusedFieldName()).toBe(focusedBefore);

    focusDebugAtStart();
    await press("ArrowLeft");
    await animationFrame();
    expect(getTitle()).toBe("Product");
    expect(".o_model_field_selector_popover").toHaveCount(1);
});

test("Enter on a relation button does not double-fire field selection", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update.bind="update"/>`;
        static props = ["*"];
        update(path) {
            expect.step(`update: ${path}`);
        }
    }

    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect(getFocusedFieldName()).toBe("Bar");

    queryOne(".o_model_field_selector_popover_item_relation").focus();
    await press("Enter");

    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect.verifySteps([]);
});

test("Enter before the search debounce fires selects what the search asked for", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update.bind="update"/>`;
        static props = ["*"];
        update(path) {
            expect.step(`update: ${path}`);
        }
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();
    expect(getFocusedFieldName()).toBe("Bar");

    await contains("input.o_input[placeholder='Search...']").edit("Product", {
        confirm: false,
    });
    await press("Enter");
    await animationFrame();
    expect.verifySteps(["update: product_id"]);
});

test("a search typed on one page does not filter the next one", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update="() => {}"/>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();

    await contains("input.o_input[placeholder='Search...']").edit("Bar", {
        confirm: false,
    });
    await followRelation();
    const displayed = getDisplayedFieldNames();
    expect(displayed).toInclude("Product Name");

    await runAllTimers();
    await animationFrame();
    expect(getDisplayedFieldNames()).toEqual(displayed);
});

test("the search box drives the field list as a combobox", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update="() => {}"/>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();

    const input = queryOne("input.o_input[placeholder='Search...']");
    const listbox = queryOne(".o_model_field_selector_popover_page");
    expect(input).toHaveAttribute("role", "combobox");
    expect(listbox).toHaveAttribute("role", "listbox");
    expect(input).toHaveAttribute("aria-controls", listbox.id);
    expect("[role=option]").toHaveCount(getDisplayedFieldNames().length);
    expect("[role=option]").toHaveClass("o_model_field_selector_popover_item_name");
    expect("[role=option] button, [role=option] input, [role=option] a").toHaveCount(0);

    const active = queryOne(
        ".o_model_field_selector_popover_item.active [role=option]",
    );
    expect(input).toHaveAttribute("aria-activedescendant", active.id);
    expect(active).toHaveAttribute("aria-selected", "true");

    await press("ArrowDown");
    await animationFrame();
    const next = queryOne(".o_model_field_selector_popover_item.active [role=option]");
    expect(next.id).not.toBe(active.id);
    expect(input).toHaveAttribute("aria-activedescendant", next.id);

    expect(".o_model_field_selector_popover_item_relation:first").toHaveAttribute(
        "tabindex",
        "-1",
    );
});

test("the first arrow after typing enters the results, it does not skip one", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update="() => {}"/>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();

    await contains("input.o_input[placeholder='Search...']").edit("o", {
        confirm: false,
    });
    const matches = ["Foo", "Product", "Last Modified on", "Created on"];

    await press("ArrowDown");
    await animationFrame();
    expect(getDisplayedFieldNames()).toEqual(matches);
    expect(getFocusedFieldName()).toBe(matches[0]);

    await press("ArrowDown");
    await animationFrame();
    expect(getFocusedFieldName()).toBe(matches[1]);
});

test("arrowing up into fresh results enters them from the end", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update="() => {}"/>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();

    const input = /** @type {HTMLInputElement} */ (
        queryOne("input.o_input[placeholder='Search...']")
    );
    await contains(input).edit("o", { confirm: false });
    input.setSelectionRange(0, 0);
    await press("ArrowUp");
    await animationFrame();
    expect(getFocusedFieldName()).toBe("Created on");
});

test("Enter on a search that matches nothing commits nothing", async () => {
    class Parent extends Component {
        static components = { ModelFieldSelector };
        static template = xml`<ModelFieldSelector resModel="'partner'" readonly="false" path="''" update.bind="update"/>`;
        static props = ["*"];
        update(path) {
            expect.step(`update: ${path}`);
        }
    }
    await mountWithCleanup(Parent);
    await openModelFieldSelectorPopover();

    await contains("input.o_input[placeholder='Search...']").edit("zzzzzz", {
        confirm: false,
    });
    await press("Enter");
    await animationFrame();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect(getDisplayedFieldNames()).toEqual([]);
    expect.verifySteps([]);
});

test("reopening a field selector supersedes metadata from its previous close", async () => {
    const selector = await mountWithCleanup(ModelFieldSelector, {
        props: {
            resModel: "partner",
            path: "foo",
            readonly: false,
            update: (path) => expect.step(path),
        },
    });
    await openModelFieldSelectorPopover();
    const metadata = new Deferred();
    patchWithCleanup(selector.fieldService, { loadFieldInfo: () => metadata });
    selector.newPath = "bar";
    const closing = selector.popover.close();
    selector.openPopover(queryOne(".o_model_field_selector"));
    metadata.resolve({ resModel: "partner", fieldDef: Partner._fields.bar });
    await closing;
    await animationFrame();
    expect.verifySteps([]);
});
