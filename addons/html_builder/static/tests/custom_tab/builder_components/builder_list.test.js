import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { expect, test, describe } from "@odoo/hoot";
import { onError, xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { press } from "@odoo/hoot-dom";

describe.current.tags("desktop");

const defaultValue = { value: "75", title: "default title" };
const defaultValueStr = JSON.stringify(defaultValue).replaceAll('"', "'");
function defaultValueWithIds(ids) {
    return ids.map((id) => ({
        ...defaultValue,
        _id: id.toString(),
    }));
}

test("writes a list of numbers to a data attribute", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                itemShape="{ value: 'number', title: 'text' }"
                default="${defaultValueStr}"
            />
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
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
                id: "a thing",
            },
            ...defaultValueWithIds([1, 2]),
        ])
    );
});

test("supports arbitrary number of text and number inputs on entries", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                itemShape="{ a: 'number', b: 'text', c: 'text', d: 'number' }"
                default="{ a: '4', b: '3', c: '2', d: '1' }"
            />
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                itemShape="{ value: 'number', title: 'text' }"
                default="${defaultValueStr}"
            />
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                itemShape="{ value: 'number', title: 'text' }"
                default="${defaultValueStr}"
            />
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
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
    class Test extends BaseOptionComponent {
        static template = xml`${template}`;
        static props = ["*"];
        setup() {
            onError(() => {
                expect.step("threw");
            });
        }
    }
    addBuilderOption({
        selector: ".test-options-target",
        Component: Test,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                itemShape="{ a: 'number', b: 'text', c: 'number', d: 'text' }"
                default="{ a: '4', b: 'three', c: '2', d: 'one' }"
                hiddenProperties="['b', 'c']"
            />
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
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
                id: "a thing",
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

test("do not lose id when adjusting 'selected'", async () => {
    class Test extends BaseOptionComponent {
        static template = xml`
            <BuilderList
                dataAttributeAction="'list'"
                addItemTitle="'Add'"
                itemShape="{ display_name: 'text', selected: 'boolean' }"
                default="{ display_name: 'Extra', selected: false }"
                records="this.availableRecords" />`;
        static props = ["*"];
        setup() {
            this.availableRecords = JSON.stringify([
                { id: 1, display_name: "A" },
                { id: 2, display_name: "B" },
            ]);
        }
    }
    addBuilderOption({
        selector: ".test-options-target",
        Component: Test,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container .o-hb-selectMany2X-toggle").click();
    await contains(".o_select_menu_menu .o-dropdown-item").click();
    await contains(".we-bg-options-container .o-hb-selectMany2X-toggle").click();
    await contains(".o_select_menu_menu .o-dropdown-item").click();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify([
            {
                id: 1,
                display_name: "A",
                _id: "0",
            },
            {
                id: 2,
                display_name: "B",
                _id: "1",
            },
        ])
    );

    await contains(".we-bg-options-container .o-hb-checkbox input").click();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify([
            {
                id: 1,
                display_name: "A",
                _id: "0",
                selected: true,
            },
            {
                id: 2,
                display_name: "B",
                _id: "1",
            },
        ])
    );

    await contains(".we-bg-options-container .o-hb-checkbox input").click();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-list",
        JSON.stringify([
            {
                id: 1,
                display_name: "A",
                _id: "0",
                selected: false,
            },
            {
                id: 2,
                display_name: "B",
                _id: "1",
            },
        ])
    );
});

test("can add item with string and integer ids", async () => {
    class Test extends BaseOptionComponent {
        static template = xml`
            <BuilderList
                dataAttributeAction="'list'"
                addItemTitle="'Add'"
                itemShape="{ display_name: 'text', selected: 'boolean' }"
                default="{ display_name: 'Extra', selected: false }"
                records="this.availableRecords" />`;
        static props = ["*"];
        setup() {
            this.availableRecords = JSON.stringify([
                {
                    id: "57cb74cc2f17a163",
                    display_name: "v1",
                },
                {
                    id: 42,
                    display_name: "v2",
                },
            ]);
        }
    }
    addBuilderOption({
        selector: ".test-options-target",
        Component: Test,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    for (let i = 0; i < 2; i++) {
        await contains(".we-bg-options-container .o-hb-selectMany2X-toggle").click();
        await contains(".o_select_menu_menu .o-dropdown-item").click();
    }
    expect(".we-bg-options-container .o-hb-selectMany2X-toggle").toHaveProperty("disabled");
});

test("not editable builder list option", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement: fieldEl }) {
                return JSON.stringify([
                    {
                        id: "test_1",
                        name: "test 1",
                        display_name: "test 1",
                        undeletable: true,
                        selected: true,
                    },
                    {
                        id: "test_2",
                        name: "test 2",
                        display_name: "test 2",
                        undeletable: true,
                        selected: false,
                    },
                ]);
            }
        },
    });
    addBuilderOption({
        selector: ".test-options-target",
        Component: class extends BaseOptionComponent {
            static template = xml`
                <BuilderList
                    action="'customAction'"
                    addItemTitle="'Add'"
                    itemShape="{ display_name: 'text', selected: 'boolean' }"
                    isEditable="false"/>`;
            static props = ["*"];
            setup() {
                this.availableRecords = JSON.stringify([
                    { id: 1, display_name: "A" },
                    { id: 2, display_name: "B" },
                ]);
            }
        },
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".we-bg-options-container .builder_list_add_item").toHaveCount(0);
    expect(".we-bg-options-container .o-hb-input-base[disabled]").toHaveCount(2);
});

test("drops blank textual entries", async () => {
    addBuilderOption({
        selector: ".test-options-target-a",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                addItemTitle="'Add'"
                itemShape="{ display_name: 'text' }"
                default="{ display_name: 'default' }"/>`,
    });
    addBuilderOption({
        selector: ".test-options-target-b",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                addItemTitle="'Add'"
                itemShape="{ display_name: 'text' }"
                default="{ display_name: 'default' }"
                forbidLastItemRemoval="true"/>`,
    });
    await setupHTMLBuilder(`
        <div class="test-options-target-a">a</div>
        <div class="test-options-target-b">b</div>`);

    // forbidLastItemRemoval="false"
    await contains(":iframe .test-options-target-a").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(".we-bg-options-container input").toHaveCount(1);

    await contains(".we-bg-options-container input").clear();
    await press("enter");
    expect(".we-bg-options-container input").toHaveCount(0);

    // forbidLastItemRemoval="true"
    await contains(":iframe .test-options-target-b").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(".we-bg-options-container input").toHaveCount(1);

    await contains(".we-bg-options-container input").clear();
    await press("enter");
    expect(".we-bg-options-container input").toHaveCount(1);
});

test("loads more items when the last row intersects", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement: fieldEl }) {
                const list = [];
                for (let i = 0; i < 150; i++) {
                    list.push({ value: `item ${i + 1}` });
                }
                return JSON.stringify(list);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderList action="'customAction'" itemShape="{ value: 'text' }"/>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">content</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".we-bg-options-container .o_row_draggable").toHaveCount(50);
    await contains(".we-bg-options-container .o_we_table_wrapper").scroll({ top: 9999 });
    expect(".we-bg-options-container .o_row_draggable").toHaveCount(100);
    await contains(".we-bg-options-container .o_we_table_wrapper").scroll({ top: 9999 });
    expect(".we-bg-options-container .o_row_draggable").toHaveCount(150);
});

test("should disable last checked checkbox", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderList
                dataAttributeAction="'list'"
                itemShape="{ value: 'boolean' }"
                default="{'value':'true'}"
                disableLastCheckedCheckbox="true"
            />`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">a</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container .builder_list_add_item").click();
    expect(".we-bg-options-container tr .o-checkbox input").toHaveAttribute("disabled");
});
