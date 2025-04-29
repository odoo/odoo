import { beforeEach, expect, test } from "@odoo/hoot";
import { click, edit, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    Country,
    Partner,
    Player,
    Product,
    Stage,
    Team,
    clearNotSupported,
    clickOnButtonDeleteNode,
    clickOnNewFilter,
    clickOnNewGroup,
    editValue,
    getOperatorOptions,
    getTreeEditorContent,
    getValueOptions,
    isNotSupportedPath,
    openModelFieldSelectorPopover,
    selectOperator,
    toggleConnector,
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

const SELECTORS = {
    ...treeEditorSELECTORS,
    debugArea: ".o_expression_editor_debug_container textarea",
};

/**
 * @param {string} value
 */
async function editExpression(value) {
    await click(SELECTORS.complexConditionInput);

    await edit(value);
    await animationFrame();
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

defineModels([Partner, Product, Team, Player, Country, Stage]);

beforeEach(() => {
    patchWithCleanup(odoo, { debug: "1" });
});

test("rendering of truthy values", async () => {
    const toTests = [`True`, `true`, `1`, `-1`, `"a"`];
    const parent = await makeExpressionEditor();
    for (const expr of toTests) {
        await parent.set(expr);
        expect(getTreeEditorContent()).toEqual([
            { level: 0, value: "all records matched (no connector value visible)" },
        ]);
    }
});

test("rendering of falsy values", async () => {
    const toTests = [`False`, `false`, `0`, `""`];
    const parent = await makeExpressionEditor();
    for (const expr of toTests) {
        await parent.set(expr);
        expect(getTreeEditorContent()).toEqual([
            { value: "Where", level: 0 },
            { value: ["0", "equal", "1"], level: 1 },
        ]);
    }
});

test("rendering of 'expr'", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "expr", level: 1 },
    ]);
    expect(queryOne(SELECTORS.complexConditionInput).readOnly).toBe(true);
});

test("rendering of 'expr' in dev mode", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "expr", level: 1 },
    ]);
    expect(queryOne(SELECTORS.complexConditionInput).readOnly).toBe(false);
});

test("edit a complex condition in dev mode", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(SELECTORS.condition).toHaveCount(0);
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await editExpression("uid");
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "uid", level: 1 },
    ]);
});

test("delete a complex condition", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await clickOnButtonDeleteNode();
    expect(getTreeEditorContent()).toEqual([
        { value: "all records matched (no connector value visible)", level: 0 },
    ]);
});

test("copy a complex condition", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(SELECTORS.condition).toHaveCount(0);
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await clickOnNewFilter();
    expect(getTreeEditorContent()).toEqual([
        { value: "And", level: 0 },
        { value: "expr", level: 1 },
        { value: ["Id", "equal", "1"], level: 1 },
    ]);
});

test("change path, operator and value", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await makeExpressionEditor({ expression: `bar != "blabla"` });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: ["Bar", "not", "blabla"] },
    ]);
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name:eq(5)").click();
    await selectOperator("not in");
    await editValue(["Doku", "Lukaku", "KDB"]);
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: ["Foo", "not in", "Doku,Lukaku,KDB"] },
    ]);
});

test("create a new branch from a complex condition control panel", async () => {
    await makeExpressionEditor({ expression: "expr" });
    expect(getTreeEditorContent()).toEqual([
        { value: "Where", level: 0 },
        { value: "expr", level: 1 },
    ]);
    await clickOnNewGroup();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: "expr" },
        { level: 1, value: "Where" },
        { level: 2, value: ["Id", "equal", "1"] },
    ]);
});

test("rendering of a valid fieldName in fields", async () => {
    const parent = await makeExpressionEditor({ fieldFilters: ["foo"] });

    const toTests = [
        { expr: `foo`, condition: ["Foo", "set"] },
        { expr: `foo == "a"`, condition: ["Foo", "equal", "a"] },
        { expr: `foo != "a"`, condition: ["Foo", "not equal", "a"] },
        { expr: `foo is "a"`, complexCondition: `foo is "a"` },
        { expr: `foo not "a"`, complexCondition: `foo not "a"` },
        { expr: `not foo`, condition: ["Foo", "not set"] },
        { expr: `foo + "a"`, complexCondition: `foo + "a"` },
    ];

    for (const { expr, condition, complexCondition } of toTests) {
        await parent.set(expr);
        const tree = getTreeEditorContent();
        if (condition) {
            expect(tree).toEqual([
                { value: "Where", level: 0 },
                { value: condition, level: 1 },
            ]);
        } else if (complexCondition) {
            expect(tree).toEqual([
                { value: "Where", level: 0 },
                { value: complexCondition, level: 1 },
            ]);
        }
    }
});

test("rendering of simple conditions", async () => {
    Partner._fields.bar = fields.Char();
    Partner._records = [];
    const parent = await makeExpressionEditor({ fieldFilters: ["foo", "bar"] });

    const toTests = [
        { expr: `bar == "a"`, condition: ["Bar", "equal", "a"] },
        { expr: `foo == expr`, condition: ["Foo", "equal", "expr"] },
        { expr: `"a" == foo`, condition: ["Foo", "equal", "a"] },
        { expr: `expr == foo`, condition: ["Foo", "equal", "expr"] },
        { expr: `foo == bar`, complexCondition: `foo == bar` },
        { expr: `"a" == "b"`, complexCondition: `"a" == "b"` },
        { expr: `expr1 == expr2`, complexCondition: `expr1 == expr2` },

        { expr: `foo < "a"`, condition: ["Foo", "lower", "a"] },
        { expr: `foo < expr`, condition: ["Foo", "lower", "expr"] },
        { expr: `"a" < foo`, condition: ["Foo", "greater", "a"] },
        { expr: `expr < foo`, condition: ["Foo", "greater", "expr"] },
        { expr: `foo < bar`, complexCondition: `foo < bar` },
        { expr: `"a" < "b"`, complexCondition: `"a" < "b"` },
        { expr: `expr1 < expr2`, complexCondition: `expr1 < expr2` },

        { expr: `foo in ["a"]`, condition: ["Foo", "in", "a"] },
        { expr: `foo in [expr]`, condition: ["Foo", "in", "expr"] },
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
                { value: "Where", level: 0 },
                { value: condition, level: 1 },
            ]);
        } else if (complexCondition) {
            expect(tree).toEqual([
                { value: "Where", level: 0 },
                { value: complexCondition, level: 1 },
            ]);
        }
    }
});

test("rendering of connectors", async () => {
    await makeExpressionEditor({ expression: `expr and foo == "abc" or not bar` });
    const tree = getTreeEditorContent();
    expect(tree).toEqual([
        { level: 0, value: "Or" },
        { level: 1, value: "And" },
        { level: 2, value: "expr" },
        { level: 2, value: ["Foo", "equal", "abc"] },
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
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "And not" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Foo", "equal", "abc"] },
    ]);
    expect.verifySteps([]);
    expect(queryOne(SELECTORS.debugArea)).toHaveValue(`not (expr or foo == "abc")`);

    await toggleConnector();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "And" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Foo", "equal", "abc"] },
    ]);
    expect.verifySteps([`expr and foo == "abc"`]);
    expect(queryOne(SELECTORS.debugArea)).toHaveValue(`expr and foo == "abc"`);
});

test("rendering of if else", async () => {
    await makeExpressionEditor({ expression: `True if False else False` });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "And" },
        { level: 1, value: "And" },
        { level: 2, value: ["0", "equal", "1"] },
        { level: 2, value: ["1", "equal", "1"] },
        { level: 1, value: "And" },
        { level: 2, value: ["1", "equal", "1"] },
        { level: 2, value: ["0", "equal", "1"] },
    ]);
});

test("check condition by default when creating a new rule", async () => {
    patchWithCleanup(odoo, { debug: "" });
    Partner._fields.country_id = fields.Char({ string: "Country ID" });
    await makeExpressionEditor({ expression: "expr" });
    await clickOnNewFilter();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "And" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Country ID", "equal", ""] },
    ]);
});

test("allow selection of boolean field", async () => {
    await makeExpressionEditor({ expression: "id" });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: ["Id", "set"] },
    ]);
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name").click();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: ["Bar", "is", "set"] },
    ]);
});

test("render false and true leaves", async () => {
    await makeExpressionEditor({ expression: `False and True` });
    expect(getOperatorOptions()).toEqual(["equal"]);
    expect(getValueOptions()).toEqual(["1"]);
    expect(getOperatorOptions(-1)).toEqual(["equal"]);
    expect(getValueOptions(-1)).toEqual(["1"]);
});

test("no field of type properties in model field selector", async () => {
    patchWithCleanup(odoo, { debug: "" });
    Partner._fields.properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "definitions",
    });
    Product._fields.definitions = fields.PropertiesDefinition();
    await makeExpressionEditor({
        expression: `properties`,
        fieldFilters: ["foo", "bar", "properties"],
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: ["Properties", "set"] },
    ]);
    expect(isNotSupportedPath()).toBe(true);
    await clearNotSupported();
    expect.verifySteps([`foo == ""`]);

    await openModelFieldSelectorPopover();
    expect(queryAllTexts(".o_model_field_selector_popover_item_name")).toEqual(["Bar", "Foo"]);
});

test("no special fields in fields", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await makeExpressionEditor({
        expression: `1`,
        fieldFilters: ["foo", "bar", "properties"],
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all records matched (no connector value visible)" },
    ]);
    await clickOnNewFilter();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "Where" },
        { level: 1, value: ["Foo", "equal", ""] },
    ]);
    expect.verifySteps([`foo == ""`]);
});

test("between operator", async () => {
    await makeExpressionEditor({
        expression: `id == 1`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getOperatorOptions()).toEqual([
        "equal",
        "not equal",
        "greater",
        "greater or equal",
        "lower",
        "lower or equal",
        "between",
        "set",
        "not set",
    ]);
    expect.verifySteps([]);
    await selectOperator("between");
    expect.verifySteps([`id >= 1 and id <= 1`]);
});

test("next operator", async () => {
    await makeExpressionEditor({
        expression: `date`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getOperatorOptions()).toEqual([
        "today",
        "not today",
        "is equal",
        "is not equal",
        "is greater",
        "is greater or equal",
        "is lower",
        "is lower or equal",
        "is between",
        "is not between",
        "next",
        "not next",
        "last",
        "not last",
        "set",
        "not set",
    ]);
    expect.verifySteps([]);
    await selectOperator("next");
    expect.verifySteps([
        `date >= context_today().strftime("%Y-%m-%d") and date <= (context_today() + relativedelta(months = 1)).strftime("%Y-%m-%d")`,
    ]);
});

test("not_next operator", async () => {
    await makeExpressionEditor({
        expression: `datetime`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getOperatorOptions()).toEqual([
        "today",
        "not today",
        "is equal",
        "is not equal",
        "is greater",
        "is greater or equal",
        "is lower",
        "is lower or equal",
        "is between",
        "is not between",
        "next",
        "not next",
        "last",
        "not last",
        "set",
        "not set",
    ]);
    expect.verifySteps([]);
    await selectOperator("not_next");
    expect.verifySteps([
        `datetime < datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") or datetime > datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
    ]);
});

test("last operator", async () => {
    await makeExpressionEditor({
        expression: `datetime`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getOperatorOptions()).toEqual([
        "today",
        "not today",
        "is equal",
        "is not equal",
        "is greater",
        "is greater or equal",
        "is lower",
        "is lower or equal",
        "is between",
        "is not between",
        "next",
        "not next",
        "last",
        "not last",
        "set",
        "not set",
    ]);
    expect.verifySteps([]);
    await selectOperator("last");
    expect.verifySteps([
        `datetime >= datetime.datetime.combine(context_today() + relativedelta(months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
    ]);
});

test("not_last operator", async () => {
    await makeExpressionEditor({
        expression: `date`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getOperatorOptions()).toEqual([
        "today",
        "not today",
        "is equal",
        "is not equal",
        "is greater",
        "is greater or equal",
        "is lower",
        "is lower or equal",
        "is between",
        "is not between",
        "next",
        "not next",
        "last",
        "not last",
        "set",
        "not set",
    ]);
    expect.verifySteps([]);
    await selectOperator("not_last");
    expect.verifySteps([
        `date < (context_today() + relativedelta(months = -1)).strftime("%Y-%m-%d") or date > context_today().strftime("%Y-%m-%d")`,
    ]);
});
