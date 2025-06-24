import { BuilderList } from "@html_builder/core/building_blocks/builder_list";
import { expect, test } from "@odoo/hoot";
import { Component, onError, xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

defineWebsiteModels();

const defaultValue = { value: "75", title: "default title" };
const defaultValueStr = JSON.stringify(defaultValue).replaceAll('"', "'");
function defaultValueWithIds(ids) {
    return ids.map((id) => ({
        ...defaultValue,
        _id: id.toString(),
    }));
}

test("writes a list of numbers to a data attribute", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderList
                          dataAttributeAction="'list'"
                          itemShape="{ value: 'number', title: 'text' }"
                          default="${defaultValueStr}"
                      />`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container .builder_list_add_item").click();
    await contains(".we-bg-options-container input[type=number]").edit("35");
    await contains(".we-bg-options-container input[type=text]").edit("a thing");
    await contains(".we-bg-options-container .builder_list_add_item").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify([
            {
                value: "35",
                title: "a thing",
                _id: "0",
            },
            ...defaultValueWithIds([1, 2]),
        ])
    );
});

test("supports arbitrary number of text and number inputs on entries", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderList
                          dataAttributeAction="'list'"
                          itemShape="{ a: 'number', b: 'text', c: 'text', d: 'number' }"
                          default="{ a: '4', b: '3', c: '2', d: '1' }"
                      />`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(".we-bg-options-container input[type=number]").toHaveCount(2);
    expect(".we-bg-options-container input[type=text]").toHaveCount(2);
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify([
            {
                a: "4",
                b: "3",
                c: "2",
                d: "1",
                _id: "0",
            },
        ])
    );
});

test("delete an item", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderList
                          dataAttributeAction="'list'"
                          itemShape="{ value: 'number', title: 'text' }"
                          default="${defaultValueStr}"
                      />`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify(defaultValueWithIds([0]))
    );
    await contains(".we-bg-options-container .builder_list_remove_item").click();
    expect(":iframe .test-options-target").toHaveAttribute("data-list", JSON.stringify([]));
});

test("reorder items", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderList
                          dataAttributeAction="'list'"
                          itemShape="{ value: 'number', title: 'text' }"
                          default="${defaultValueStr}"
                      />`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container .builder_list_add_item").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    function expectOrder(ids) {
        expect(":iframe .test-options-target").toHaveAttribute(
            "data-list",
            JSON.stringify(defaultValueWithIds(ids))
        );
    }
    expectOrder([0, 1, 2]);

    const rowSelector = (id) => `.we-bg-options-container .o_row_draggable[data-id="${id}"]`;
    const rowHandleSelector = (id) => `${rowSelector(id)} .o_handle_cell`;

    await contains(rowHandleSelector(0)).dragAndDrop(rowSelector(1));
    expectOrder([1, 0, 2]);

    await contains(rowHandleSelector(1)).dragAndDrop(rowSelector(2));
    expectOrder([0, 2, 1]);

    await contains(rowHandleSelector(1)).dragAndDrop(rowSelector(0));
    expectOrder([1, 0, 2]);

    await contains(rowHandleSelector(2)).dragAndDrop(rowSelector(0));
    expectOrder([1, 2, 0]);

    await contains(rowHandleSelector(2)).dragAndDrop(rowSelector(0));
    expectOrder([1, 0, 2]);

    await contains(rowHandleSelector(0)).dragAndDrop(rowSelector(1));
    expectOrder([0, 1, 2]);
});

async function testBuilderListFaultyProps(template) {
    class Test extends Component {
        static template = xml`${template}`;
        static components = { BuilderList };
        static props = ["*"];
        setup() {
            onError(() => {
                expect.step("threw");
            });
        }
    }
    addOption({
        selector: ".test-options-target",
        Component: Test,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect.verifySteps(["threw"]);
}
test("throws error on empty shape", async () => {
    await testBuilderListFaultyProps(`
        <BuilderList
            dataAttributeAction="'list'"
            itemShape="{}"
            default="{}"
        />
    `);
});

test("throws error on wrong item shape types", async () => {
    await testBuilderListFaultyProps(`
        <BuilderList
            dataAttributeAction="'list'"
            itemShape="{ a: 'doesnotexist' }"
            default="{ a: '1' }"
        />
    `);
});

test("throws error on wrong properties default value", async () => {
    await testBuilderListFaultyProps(`
        <BuilderList
            dataAttributeAction="'list'"
            itemShape="{ a: 'number' }"
            default="{ b: '1' }"
        />
    `);
});

test("throws error on missing default value with a custom itemShape", async () => {
    await testBuilderListFaultyProps(`
        <BuilderList
            dataAttributeAction="'list'"
            itemShape="{ a: 'number', b: 'text' }"
        />
    `);
});

test("throws error if itemShape contains reserved key '_id'", async () => {
    await testBuilderListFaultyProps(`
        <BuilderList
            dataAttributeAction="'list'"
            itemShape="{ _id: 'number' }"
            default="{ _id: '1' }"
        />
    `);
});

test("hides hiddenProperties from options", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderList
                          dataAttributeAction="'list'"
                          itemShape="{ a: 'number', b: 'text', c: 'number', d: 'text' }"
                          default="{ a: '4', b: 'three', c: '2', d: 'one' }"
                          hiddenProperties="['b', 'c']"
                      />`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(".we-bg-options-container input[type=number]").toHaveCount(1);
    expect(".we-bg-options-container input[type=text]").toHaveCount(1);
    await contains(".we-bg-options-container input[type=number]").edit("35");
    await contains(".we-bg-options-container input[type=text]").edit("a thing");
    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify([
            {
                a: "35",
                b: "three",
                c: "2",
                d: "a thing",
                _id: "0",
            },
            {
                a: "4",
                b: "three",
                c: "2",
                d: "one",
                _id: "1",
            },
        ])
    );
});
