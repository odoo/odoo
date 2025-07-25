import { beforeEach, expect, test } from "@odoo/hoot";
import { click, edit, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    addNewRule,
    clearNotSupported,
    clickOnButtonAddBranch,
    clickOnButtonAddRule,
    clickOnButtonDeleteNode,
    Country,
    editValue,
    formatExpr,
    getCurrentOperator,
    getCurrentValue,
    getOperatorOptions,
    getTreeEditorContent,
    getValueOptions,
    isNotSupportedPath,
    label,
    openModelFieldSelectorPopover,
    Partner,
    Player,
    Product,
    selectOperator,
    selectValue,
    Stage,
    Team,
    toggleConnector,
    SELECTORS as treeEditorSELECTORS,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    mountWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { ExpressionEditor } from "@web/core/expression_editor/expression_editor";

import { getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
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
    serverState.debug = "1";
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
            { value: ["0", label("="), "1"], level: 1 },
        ]);
    }
});

test("rendering of 'expr'", async () => {
    serverState.debug = "";
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
    await editExpression("uid");
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
    await clickOnButtonAddBranch();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: "any" },
        { level: 2, value: "expr" },
    ]);
    await clickOnButtonAddRule();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: "any" },
        { level: 2, value: "expr" },
        { level: 2, value: "expr" },
    ]);
});

test("change path, operator and value", async () => {
    serverState.debug = "";
    await makeExpressionEditor({ expression: `bar != "blabla"` });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Bar", label("!="), "blabla"] },
    ]);
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name:eq(5)").click();
    await selectOperator("=");
    await editValue("Doku");
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Foo", label("="), "Doku"] },
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
        { level: 2, value: "expr" },
    ]);
});

test("rendering of a valid fieldName in fields", async () => {
    const parent = await makeExpressionEditor({ fieldFilters: ["foo"] });

    const toTests = [
        { expr: `foo`, condition: ["Foo", label("set")] },
        { expr: `foo == "a"`, condition: ["Foo", label("="), "a"] },
        { expr: `foo != "a"`, condition: ["Foo", label("!="), "a"] },
        // { expr: `foo is "a"`, complexCondition: `foo is "a"` },
        // { expr: `foo is not "a"`, complexCondition: `foo is not "a"` },
        { expr: `not foo`, condition: ["Foo", label("not set")] },
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
    Partner._fields.bar = fields.Char();
    Partner._records = [];
    const parent = await makeExpressionEditor({ fieldFilters: ["foo", "bar"] });

    const toTests = [
        { expr: `bar == "a"`, condition: ["Bar", label("="), "a"] },
        { expr: `foo == expr`, condition: ["Foo", label("="), "expr"] },
        { expr: `"a" == foo`, condition: ["Foo", label("="), "a"] },
        { expr: `expr == foo`, condition: ["Foo", label("="), "expr"] },
        { expr: `foo == bar`, complexCondition: `foo == bar` },
        { expr: `"a" == "b"`, complexCondition: `"a" == "b"` },
        { expr: `expr1 == expr2`, complexCondition: `expr1 == expr2` },

        { expr: `foo < "a"`, condition: ["Foo", label("<"), "a"] },
        { expr: `foo < expr`, condition: ["Foo", label("<"), "expr"] },
        { expr: `"a" < foo`, condition: ["Foo", label(">"), "a"] },
        { expr: `expr < foo`, condition: ["Foo", label(">"), "expr"] },
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
    expect(queryAllTexts(SELECTORS.connectorValue)).toEqual(["any", "all"]);
    const tree = getTreeEditorContent();
    expect(tree).toEqual([
        { level: 0, value: "any" },
        { level: 1, value: "all" },
        { level: 2, value: "expr" },
        { level: 2, value: ["Foo", label("="), "abc"] },
        { level: 1, value: ["Bar", label("not set")] },
    ]);
});

test("rendering of connectors (2)", async () => {
    await makeExpressionEditor({
        expression: `not (expr or foo == "abc")`,
        update(expression) {
            expect.step(expression);
        },
    });
    expect(SELECTORS.connectorValue).toHaveText("none");
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "none" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Foo", label("="), "abc"] },
    ]);
    expect.verifySteps([]);
    expect(queryOne(SELECTORS.debugArea)).toHaveValue(`not (expr or foo == "abc")`);

    await toggleConnector();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Foo", label("="), "abc"] },
    ]);
    expect.verifySteps([`expr and foo == "abc"`]);
    expect(queryOne(SELECTORS.debugArea)).toHaveValue(`expr and foo == "abc"`);
});

test("rendering of if else", async () => {
    await makeExpressionEditor({ expression: `True if False else False` });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "any" },
        { level: 1, value: "all" },
        { level: 2, value: ["0", label("="), "1"] },
        { level: 2, value: ["1", label("="), "1"] },
        { level: 1, value: "all" },
        { level: 2, value: ["1", label("="), "1"] },
        { level: 2, value: ["0", label("="), "1"] },
    ]);
});

test("check condition by default when creating a new rule", async () => {
    serverState.debug = "";
    Partner._fields.country_id = fields.Char({ string: "Country ID" });
    await makeExpressionEditor({ expression: "expr" });
    await contains("a[role='button']").click();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: "expr" },
        { level: 1, value: ["Country ID", label("="), ""] },
    ]);
});

test("allow selection of boolean field", async () => {
    await makeExpressionEditor({ expression: "id" });
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Id", label("set")] },
    ]);
    await openModelFieldSelectorPopover();
    await contains(".o_model_field_selector_popover_item_name").click();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Bar", label("set")] },
    ]);
});

test("render false and true leaves", async () => {
    await makeExpressionEditor({ expression: `False and True` });
    expect(getOperatorOptions()).toEqual([label("=")]);
    expect(getValueOptions()).toEqual(["1"]);
    expect(getOperatorOptions(-1)).toEqual([label("=")]);
    expect(getValueOptions(-1)).toEqual(["1"]);
});

test("no field of type properties in model field selector", async () => {
    serverState.debug = "";
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
        { level: 0, value: "all" },
        { level: 1, value: ["Properties", label("set")] },
    ]);
    expect(isNotSupportedPath()).toBe(true);
    await clearNotSupported();
    expect.verifySteps([`foo == ""`]);

    await openModelFieldSelectorPopover();
    expect(queryAllTexts(".o_model_field_selector_popover_item_name")).toEqual(["Bar", "Foo"]);
});

test("no special fields in fields", async () => {
    serverState.debug = "";
    await makeExpressionEditor({
        expression: `True`,
        fieldFilters: ["foo", "bar", "properties"],
        update(expression) {
            expect.step(expression);
        },
    });
    expect(getTreeEditorContent()).toEqual([{ level: 0, value: "all" }]);
    await addNewRule();
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        { level: 1, value: ["Foo", label("="), ""] },
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
        label("="),
        label("!="),
        label("<"),
        label(">"),
        label("between"),
    ]);
    expect.verifySteps([]);
    await selectOperator("between");
    expect.verifySteps([`id >= 1 and id <= 1`]);
});

test(`"in range" operator`, async () => {
    await makeExpressionEditor({
        expression: `date`,
        update(expression) {
            expect.step(expression);
        },
    });
    await selectOperator("in range");
    expect.verifySteps([
        formatExpr(
            `
                date >= context_today().strftime("%Y-%m-%d")
                    and
                date < (context_today() + relativedelta(days = 1)).strftime("%Y-%m-%d")
            `
        ),
    ]);
    expect(getTreeEditorContent()).toEqual([
        { level: 0, value: "all" },
        {
            level: 1,
            value: ["Date", "is in", "Today"],
        },
    ]);
});

test(`date: "in range" operator`, async () => {
    mockDate("2023-04-20 17:00:00", 0);
    await makeExpressionEditor({
        expression: `id`,
        update(expression) {
            expect.step(expression);
        },
    });
    await openModelFieldSelectorPopover();
    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_popover_item_name:eq(2)"
    ).click();
    expect(getCurrentOperator()).toBe(label("in range"));
    expect(getCurrentValue()).toBe("Today");
    expect.verifySteps([
        formatExpr(
            `date >= context_today().strftime("%Y-%m-%d") and date < (context_today() + relativedelta(days = 1)).strftime("%Y-%m-%d")`
        ),
    ]);

    expect(getValueOptions()).toEqual([
        "Today",
        "Last 7 days",
        "Last 30 days",
        "Month to date",
        "Last month",
        "Year to date",
        "Last 12 months",
        "Custom range",
    ]);

    await selectValue("last 7 days");
    expect(getCurrentValue()).toBe("Last 7 days");
    expect.verifySteps([
        formatExpr(
            `date >= (context_today() + relativedelta(days = -7)).strftime("%Y-%m-%d") and date < context_today().strftime("%Y-%m-%d")`
        ),
    ]);

    await selectValue("last 30 days");
    expect(getCurrentValue()).toBe("Last 30 days");
    expect.verifySteps([
        formatExpr(
            `date >= (context_today() + relativedelta(days = -30)).strftime("%Y-%m-%d") and date < context_today().strftime("%Y-%m-%d")`
        ),
    ]);

    await selectValue("month to date");
    expect(getCurrentValue()).toBe("Month to date");
    expect.verifySteps([
        formatExpr(
            `date >= (context_today() + relativedelta(day = 1)).strftime("%Y-%m-%d") and date < (context_today() + relativedelta(days = 1)).strftime("%Y-%m-%d")`
        ),
    ]);

    await selectValue("last month");
    expect(getCurrentValue()).toBe("Last month");
    expect.verifySteps([
        formatExpr(
            `date >= (context_today() + relativedelta(day = 1, months = -1)).strftime("%Y-%m-%d") and date < (context_today() + relativedelta(day = 1)).strftime("%Y-%m-%d")`
        ),
    ]);

    await selectValue("year to date");
    expect(getCurrentValue()).toBe("Year to date");
    expect.verifySteps([
        formatExpr(
            `date >= (context_today() + relativedelta(day = 1, month = 1)).strftime("%Y-%m-%d") and date < (context_today() + relativedelta(days = 1)).strftime("%Y-%m-%d")`
        ),
    ]);

    await selectValue("last 12 months");
    expect(getCurrentValue()).toBe("Last 12 months");
    expect.verifySteps([
        formatExpr(
            `date >= (context_today() + relativedelta(day = 1, months = -12)).strftime("%Y-%m-%d") and date < (context_today() + relativedelta(day = 1)).strftime("%Y-%m-%d")`
        ),
    ]);

    await selectValue("custom range");
    expect(queryOne(`${SELECTORS.valueEditor} select`).value).toBe('"custom range"');
    expect.verifySteps([formatExpr(`date >= "2023-04-20" and date <= "2023-04-20"`)]);

    await contains(".o_datetime_input:last").click();
    await contains(getPickerCell("26", true)).click();
    await press("enter");
    await animationFrame();
    expect.verifySteps([formatExpr(`date >= "2023-04-20" and date <= "2023-04-26"`)]);

    await selectValue("today");
    expect(getCurrentOperator()).toBe(label("in range"));
    expect(getCurrentValue()).toBe("Today");
    expect.verifySteps([
        formatExpr(
            `date >= context_today().strftime("%Y-%m-%d") and date < (context_today() + relativedelta(days = 1)).strftime("%Y-%m-%d")`
        ),
    ]);
});

test(`datetime: "in range" operator`, async () => {
    mockDate("2023-04-20 17:00:00", 0);
    await makeExpressionEditor({
        expression: `id`,
        update(expression) {
            expect.step(expression);
        },
    });
    await openModelFieldSelectorPopover();
    await contains(
        ".o_model_field_selector_popover .o_model_field_selector_popover_item_name:eq(3)"
    ).click();
    expect(getCurrentOperator()).toBe(label("in range"));
    expect(getCurrentValue()).toBe("Today");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    expect(getValueOptions()).toEqual([
        "Today",
        "Last 7 days",
        "Last 30 days",
        "Month to date",
        "Last month",
        "Year to date",
        "Last 12 months",
        "Custom range",
    ]);

    await selectValue("last 7 days");
    expect(getCurrentValue()).toBe("Last 7 days");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today() + relativedelta(days = -7), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    await selectValue("last 30 days");
    expect(getCurrentValue()).toBe("Last 30 days");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today() + relativedelta(days = -30), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    await selectValue("month to date");
    expect(getCurrentValue()).toBe("Month to date");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today() + relativedelta(day = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    await selectValue("last month");
    expect(getCurrentValue()).toBe("Last month");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today() + relativedelta(day = 1, months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today() + relativedelta(day = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    await selectValue("year to date");
    expect(getCurrentValue()).toBe("Year to date");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today() + relativedelta(day = 1, month = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    await selectValue("last 12 months");
    expect(getCurrentValue()).toBe("Last 12 months");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today() + relativedelta(day = 1, months = -12), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today() + relativedelta(day = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);

    await selectValue("custom range");
    expect(queryOne(`${SELECTORS.valueEditor} select`).value).toBe('"custom range"');
    expect.verifySteps([
        formatExpr(`datetime >= "2023-04-20 00:00:00" and datetime <= "2023-04-20 23:59:59"`),
    ]);

    await contains(".o_datetime_input:last").click();
    await contains(getPickerCell("26", true)).click();
    await press("enter");
    await animationFrame();
    expect.verifySteps([
        formatExpr(`datetime >= "2023-04-20 00:00:00" and datetime <= "2023-04-26 23:59:59"`),
    ]);

    await selectValue("today");
    expect(getCurrentOperator()).toBe(label("in range"));
    expect(getCurrentValue()).toBe("Today");
    expect.verifySteps([
        formatExpr(
            `
                datetime >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
                    and
                datetime < datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")
            `
        ),
    ]);
});
