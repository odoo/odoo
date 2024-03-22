import { beforeEach, expect, test } from "@odoo/hoot";
import { click, edit, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    Partner,
    Product,
    clearNotSupported,
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    clickOnButtonDeleteNode,
    editValue,
    get,
    getOperatorOptions,
    getTreeEditorContent,
    getValueOptions,
    isNotSupportedPath,
    openModelFieldSelectorPopover,
    selectOperator,
    SELECTORS as treeEditorSELECTORS,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { ExpressionEditor } from "@web/core/expression_editor/expression_editor";

import { Component, xml } from "@odoo/owl";
import { pick } from "@web/core/utils/objects";

export const SELECTORS = {
    ...treeEditorSELECTORS,
    debugArea: ".o_expression_editor_debug_container textarea",
};

function editExpression(value, index = 0) {
    const input = get(SELECTORS.complexConditionInput, index);
    click(input);
    edit(value);
}

async function selectConnector(value, index = 0) {
    const toggler = get(`${SELECTORS.connector} .dropdown-toggle`, index);
    await contains(toggler).click();
    const dropdownMenu = get(`${SELECTORS.connector} .dropdown-menu `, index);
    await contains(`.dropdown-item:contains(${value})`, { root: dropdownMenu }).click();
}

async function makeExpressionEditor(params = {}) {
    const fieldFilters = params.fieldFilters;
    delete params.fieldFilters;
    const props = { ...params };
    class Parent extends Component {
        static components = { ExpressionEditor };
        static template = xml`<ExpressionEditor t-props="expressionEditorProps"/>`;
        static props = ["*"];
        setup() {
            this.expressionEditorProps = {
                expression: "1",
                ...props,
                resModel: "partner",
                update: (expression) => {
                    if (props.update) {
                        props.update(expression);
                    }
                    this.expressionEditorProps.expression = expression;
                    this.render();
                },
            };
            this.expressionEditorProps.fields = fieldFilters
                ? pick(Partner._fields, ...fieldFilters)
                : Partner._fields;
        }
        async set(expression) {
            this.expressionEditorProps.expression = expression;
            this.render();
            await animationFrame();
        }
    }

    return mountWithCleanup(Parent, { props });
}

defineModels([Partner, Product]);

beforeEach(() => {
    patchWithCleanup(odoo, { debug: true });
});

test("rendering of truthy values", async () => {
    const toTests = [`True`, `true`, `1`, `-1`, `"a"`];
    const parent = await makeExpressionEditor();
    for (const expr of toTests) {
        await parent.set(expr);
        expect(getTreeEditorContent()).toEqual([{ level: 0, value: "all" }]);
    }
});

test("rendering of falsy values", async () => {
    const toTests = [`False`, `false`, `0`, `""`];
    const parent = await makeExpressionEditor();
    for (const expr of toTests) {
        await parent.set(expr);
        expect(getTreeEditorContent()).toEqual([
            { value: "all", level: 0 },
            { value: ["0", "=", "1"], level: 1 },
        ]);
    }
});

test("rendering of 'expr'", async () => {
    patchWithCleanup(odoo, { debug: false });
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
    ]);
    expect(queryOne(SELECTORS.complexConditionInput).readOnly).toBe(true);
});

test("rendering of 'expr' in dev mode", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
    ]);
    expect(queryOne(SELECTORS.complexConditionInput).readOnly).toBe(false);
});

test("edit a complex condition in dev mode", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(SELECTORS.condition).toHaveCount(0);
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
    ]);
    editExpression("uid");
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "uid", level: 1 },
    ]);
});

test("delete a complex condition", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await clickOnButtonDeleteNode();
    expect(getTreeEditorContent()).toEqual([{ value: "all", level: 0 }]);
});

test("copy a complex condition", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(SELECTORS.condition).toHaveCount(0);
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await clickOnButtonAddNewRule();
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
        { value: "expr", level: 1 },
    ]);
});

test("change path, operator and value", async () => {
    patchWithCleanup(odoo, { debug: false });
    await makeExpressionEditor({ expression: `bar != "blabla"` });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Bar", "is not", "blabla"] },
    ]);
    const tree = getTreeEditorContent({ node: true });
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name:eq(5)").click();
    await selectOperator("not in", tree[1].node);
    await editValue(["Doku", "Lukaku", "KDB"]);
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Foo", "is not in", "Doku,Lukaku,KDB"] },
    ]);
});

test("create a new branch from a complex condition control panel", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "all", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await clickOnButtonAddBranch();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: "any" },
        { level: 2, value: ["Id", "=", "1"] },
        { level: 2, value: ["Id", "=", "1"] },
    ]);
});

test("rendering of a valid fieldName in fields", async () => {
    Partner._fields.foo = fields.Char({ string: "Foo", searchable: true });
    const parent = await makeExpressionEditor({ fieldFilters: ["foo"] });

    const toTests = [
        { expr: `foo`, condition: ["Foo", "is set"] },
        { expr: `foo == "a"`, condition: ["Foo", "=", "a"] },
        { expr: `foo != "a"`, condition: ["Foo", "!=", "a"] },
        // { expr: `foo is "a"`, complexCondition: `foo is "a"` },
        // { expr: `foo is not "a"`, complexCondition: `foo is not "a"` },
        { expr: `not foo`, condition: ["Foo", "is not set"] },
        { expr: `foo + "a"`, complexCondition: `foo + "a"` },
    ];

    for (const { expr, condition, complexCondition } of toTests) {
        await parent.set(expr);
        const tree = getTreeEditorContent();
        if (condition) {
            expect(tree).toEqual([
                { value: "all", level: 0 },
                { value: condition, level: 1 },
            ]);
        } else if (complexCondition) {
            expect(tree).toEqual([
                { value: "all", level: 0 },
                { value: complexCondition, level: 1 },
            ]);
        }
    }
});

test("rendering of simple conditions", async () => {
    Partner._fields.foo = fields.Char({ string: "Foo", searchable: true });
    Partner._fields.bar = fields.Char({ string: "Bar", searchable: true });
    Partner._records = [];
    const parent = await makeExpressionEditor({ fieldFilters: ["foo", "bar"] });

    const toTests = [
        { expr: `bar == "a"`, condition: ["Bar", "=", "a"] },
        { expr: `foo == expr`, condition: ["Foo", "=", "expr"] },
        { expr: `"a" == foo`, condition: ["Foo", "=", "a"] },
        { expr: `expr == foo`, condition: ["Foo", "=", "expr"] },
        { expr: `foo == bar`, complexCondition: `foo == bar` },
        { expr: `"a" == "b"`, complexCondition: `"a" == "b"` },
        { expr: `expr1 == expr2`, complexCondition: `expr1 == expr2` },

        { expr: `foo < "a"`, condition: ["Foo", "<", "a"] },
        { expr: `foo < expr`, condition: ["Foo", "<", "expr"] },
        { expr: `"a" < foo`, condition: ["Foo", ">", "a"] },
        { expr: `expr < foo`, condition: ["Foo", ">", "expr"] },
        { expr: `foo < bar`, complexCondition: `foo < bar` },
        { expr: `"a" < "b"`, complexCondition: `"a" < "b"` },
        { expr: `expr1 < expr2`, complexCondition: `expr1 < expr2` },

        { expr: `foo in ["a"]`, condition: ["Foo", "is in", "a"] },
        { expr: `foo in [expr]`, condition: ["Foo", "is in", "expr"] },
        { expr: `"a" in foo`, complexCondition: `"a" in foo` },
        { expr: `expr in foo`, complexCondition: `expr in foo` },
        { expr: `foo in bar`, complexCondition: `foo in bar` },
        { expr: `"a" in "b"`, complexCondition: `"a" in "b"` },
        { expr: `expr1 in expr2`, complexCondition: `expr1 in expr2` },
    ];

    for (const { expr, condition, complexCondition } of toTests) {
        await parent.set(expr);
        const tree = getTreeEditorContent();
        if (condition) {
            expect(tree).toEqual([
                { value: "all", level: 0 },
                { value: condition, level: 1 },
            ]);
        } else if (complexCondition) {
            expect(tree).toEqual([
                { value: "all", level: 0 },
                { value: complexCondition, level: 1 },
            ]);
        }
    }
});

test("rendering of connectors", async () => {
    await makeExpressionEditor({ expression: `expr and foo == "abc" or not bar` });
    expect(queryAllTexts(`${SELECTORS.connector} .dropdown-toggle`)).toEqual(["any", "all"]);
    const tree = getTreeEditorContent();
    expect(tree).toEqual([
        { level: 0, value: "any" },
        { level: 1, value: "all" },
        { level: 2, value: "expr" },
        { level: 2, value: ["Foo", "=", "abc"] },
        { level: 1, value: ["Bar", "is", "not set"] },
    ]);
});

test("rendering of connectors (2)", async () => {
    await makeExpressionEditor({
        expression: `not (expr or foo == "abc")`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(queryOne(`${SELECTORS.connector} .dropdown-toggle`)).toHaveText("none");
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "none" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Foo", "=", "abc"] },
    ]);
    expect([]).toVerifySteps();
    expect(queryOne(SELECTORS.debugArea)).toHaveValue(`not (expr or foo == "abc")`);

    await selectConnector("all");
    expect(queryOne(`${SELECTORS.connector} .dropdown-toggle`)).toHaveText("all");
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Foo", "=", "abc"] },
    ]);
    expect([`expr and foo == "abc"`]).toVerifySteps();
    expect(queryOne(SELECTORS.debugArea)).toHaveValue(`expr and foo == "abc"`);
});

test("rendering of if else", async () => {
    await makeExpressionEditor({ expression: `True if False else False` });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "any" },
        { level: 1, value: "all" },
        { level: 2, value: ["0", "=", "1"] },
        { level: 2, value: ["1", "=", "1"] },
        { level: 1, value: "all" },
        { level: 2, value: ["1", "=", "1"] },
        { level: 2, value: ["0", "=", "1"] },
    ]);
});

test("check condition by default when creating a new rule", async () => {
    patchWithCleanup(odoo, { debug: false });
    Partner._fields.country_id = fields.Char({ string: "Country ID" });
    await makeExpressionEditor({ expression: "expr" });
    await contains("a[role='button']").click();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Country ID", "=", ""] },
    ]);
});

test("allow selection of boolean field", async () => {
    await makeExpressionEditor({ expression: "id" });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Id", "is set"] },
    ]);
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name").click();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Bar", "is", "set"] },
    ]);
});

test("render false and true leaves", async () => {
    await makeExpressionEditor({ expression: `False and True` });
    expect(getOperatorOptions()).toEqual(["="]);
    expect(getValueOptions()).toEqual(["1"]);
    expect(getOperatorOptions(-1)).toEqual(["="]);
    expect(getValueOptions(-1)).toEqual(["1"]);
});

test("no field of type properties in model field selector", async () => {
    patchWithCleanup(odoo, { debug: false });
    Partner._fields.properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
        searchable: true,
    });
    Product._fields.definitions = fields.PropertiesDefinition({ string: "Definitions" });
    await makeExpressionEditor({
        expression: `properties`,
        fieldFilters: ["foo", "bar", "properties"],
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Properties", "is set"] },
    ]);
    expect(isNotSupportedPath()).toBe(true);
    await clearNotSupported();
    expect([`foo == ""`]).toVerifySteps();

    await openModelFieldSelectorPopover();
    expect(queryAllTexts(".o_model_field_selector_popover_item_name")).toEqual(["Bar", "Foo"]);
});

test("between operator", async () => {
    await makeExpressionEditor({
        expression: `id == 1`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getOperatorOptions()).toEqual([
        "=",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
        "is between",
        "is set",
        "is not set",
    ]);
    expect([]).toVerifySteps();
    await selectOperator("between");
    expect([`id >= 1 and id <= 1`]).toVerifySteps();
});
