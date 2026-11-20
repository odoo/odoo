/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    mount,
    nextTick,
    patchWithCleanup,
} from "../helpers/utils";
import { Component, xml } from "@odoo/owl";
import { ExpressionEditor } from "@web/core/expression_editor/expression_editor";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { makeTestEnv } from "../helpers/mock_env";
import {
    SELECTORS as treeEditorSELECTORS,
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    clickOnButtonDeleteNode,
    editValue,
    get,
    getTreeEditorContent,
    makeServerData,
    selectOperator,
    setupConditionTreeEditorServices,
    getOperatorOptions,
    getValueOptions,
    isNotSupportedPath,
    clearNotSupported,
} from "./condition_tree_editor_helpers";
import { openModelFieldSelectorPopover } from "./model_field_selector_tests";

export {
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    clickOnButtonDeleteNode,
    editValue,
    get,
    getTreeEditorContent,
    makeServerData,
    selectOperator,
    setupConditionTreeEditorServices,
    isNotSupportedPath,
    clearNotSupported,
} from "./condition_tree_editor_helpers";

let serverData;
let target;

export const SELECTORS = {
    ...treeEditorSELECTORS,
    debugArea: ".o_expression_editor_debug_container textarea",
};

async function editExpression(target, value, index = 0) {
    const input = get(target, SELECTORS.complexConditionInput, index);
    await editInput(input, null, value);
}

async function selectConnector(target, value, index = 0) {
    const toggler = get(target, `${SELECTORS.connector} .dropdown-toggle`, index);
    await click(toggler);
    const dropdownMenu = get(target, `${SELECTORS.connector} .dropdown-menu `, index);
    const items = [...dropdownMenu.querySelectorAll(".dropdown-item")];
    const item = items.find((i) => i.innerText === value);
    await click(item);
}

async function makeExpressionEditor(params = {}) {
    const props = { ...params };
    const mockRPC = props.mockRPC;
    delete props.mockRPC;

    class Parent extends Component {
        setup() {
            this.expressionEditorProps = {
                resModel: "partner",
                expression: "1",
                ...props,
                update: (expression) => {
                    if (props.update) {
                        props.update(expression);
                    }
                    this.expressionEditorProps.expression = expression;
                    this.render();
                },
            };
            this.expressionEditorProps.fields =
                this.expressionEditorProps.fields ||
                serverData.models[this.expressionEditorProps.resModel]?.fields ||
                {};
            Object.entries(this.expressionEditorProps.fields).forEach(([fieldName, field]) => {
                field.name = fieldName;
            });
        }
        async set(expression) {
            this.expressionEditorProps.expression = expression;
            this.render();
            await nextTick();
        }
    }
    Parent.components = { ExpressionEditor };
    Parent.template = xml`<ExpressionEditor t-props="expressionEditorProps"/>`;

    const env = await makeTestEnv({ serverData, mockRPC });
    await mount(MainComponentsContainer, target, { env });
    return mount(Parent, target, { env, props });
}

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = makeServerData();
        setupConditionTreeEditorServices();
        target = getFixture();
        patchWithCleanup(odoo, { debug: true });
    });

    QUnit.module("ExpressionEditor");

    QUnit.test("rendering of truthy values", async (assert) => {
        const toTests = [`True`, `true`, `1`, `-1`, `"a"`];
        const parent = await makeExpressionEditor();

        for (const expr of toTests) {
            await parent.set(expr);
            const tree = getTreeEditorContent(target);
            assert.deepEqual(tree, [{ level: 0, value: "all" }]);
        }
    });

    QUnit.test("rendering of falsy values", async (assert) => {
        const toTests = [`False`, `false`, `0`, `""`];
        const parent = await makeExpressionEditor();
        for (const expr of toTests) {
            await parent.set(expr);
            assert.deepEqual(getTreeEditorContent(target), [
                { value: "all", level: 0 },
                { value: ["0", "=", "1"], level: 1 },
            ]);
        }
    });

    QUnit.test("rendering of 'expr'", async (assert) => {
        patchWithCleanup(odoo, { debug: false });
        await makeExpressionEditor({ expression: "expr" });
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
        ]);
        assert.strictEqual(target.querySelector(SELECTORS.complexConditionInput).readOnly, true);
    });

    QUnit.test("rendering of 'expr' in dev mode", async (assert) => {
        await makeExpressionEditor({ expression: "expr" });
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
        ]);
        assert.strictEqual(target.querySelector(SELECTORS.complexConditionInput).readOnly, false);
    });

    QUnit.test("edit a complex condition in dev mode", async (assert) => {
        await makeExpressionEditor({ expression: "expr" });
        assert.containsNone(target, SELECTORS.condition);
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
        ]);
        await editExpression(target, "uid");
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "uid", level: 1 },
        ]);
    });

    QUnit.test("delete a complex condition", async (assert) => {
        await makeExpressionEditor({ expression: "expr" });
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
        ]);
        await clickOnButtonDeleteNode(target);
        assert.deepEqual(getTreeEditorContent(target), [{ value: "all", level: 0 }]);
    });

    QUnit.test("copy a complex condition", async (assert) => {
        await makeExpressionEditor({ expression: "expr" });
        assert.containsNone(target, SELECTORS.condition);
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
        ]);
        await clickOnButtonAddNewRule(target);
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
            { value: "expr", level: 1 },
        ]);
    });

    QUnit.test("change path, operator and value", async (assert) => {
        patchWithCleanup(odoo, { debug: false });
        await makeExpressionEditor({ expression: `bar != "blabla"` });
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "all" },
            { level: 1, value: ["Bar", "is not", "blabla"] },
        ]);
        const tree = getTreeEditorContent(target, { node: true });
        await openModelFieldSelectorPopover(target);
        await click(target.querySelectorAll(".o_model_field_selector_popover_item_name")[4]);
        await selectOperator(tree[1].node, "not in");
        await editValue(target, ["Doku", "Lukaku", "KDB"]);
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "all" },
            { level: 1, value: ["Foo", "is not in", "Doku,Lukaku,KDB"] },
        ]);
    });

    QUnit.test("create a new branch from a complex condition control panel", async (assert) => {
        await makeExpressionEditor({ expression: "expr" });
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
        ]);
        await clickOnButtonAddBranch(target);
        assert.deepEqual(getTreeEditorContent(target), [
            { value: "all", level: 0 },
            { value: "expr", level: 1 },
            { level: 1, value: "any" },
            { level: 2, value: ["ID", "=", "1"] },
            { level: 2, value: ["ID", "=", "1"] },
        ]);
    });

    QUnit.test("rendering of a valid fieldName in fields", async (assert) => {
        const fields = { foo: { string: "Foo", type: "char", searchable: true } };
        const parent = await makeExpressionEditor({ fields });

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
            const tree = getTreeEditorContent(target);
            if (condition) {
                assert.deepEqual(tree, [
                    { value: "all", level: 0 },
                    { value: condition, level: 1 },
                ]);
            } else if (complexCondition) {
                assert.deepEqual(tree, [
                    { value: "all", level: 0 },
                    { value: complexCondition, level: 1 },
                ]);
            }
        }
    });

    QUnit.test("rendering of simple conditions", async (assert) => {
        const fields = {
            foo: { string: "Foo", type: "char", searchable: true },
            bar: { string: "Bar", type: "char", searchable: true },
        };
        const parent = await makeExpressionEditor({ fields });

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
            const tree = getTreeEditorContent(target);
            if (condition) {
                assert.deepEqual(tree, [
                    { value: "all", level: 0 },
                    { value: condition, level: 1 },
                ]);
            } else if (complexCondition) {
                assert.deepEqual(tree, [
                    { value: "all", level: 0 },
                    { value: complexCondition, level: 1 },
                ]);
            }
        }
    });

    QUnit.test("rendering of connectors", async (assert) => {
        await makeExpressionEditor({ expression: `expr and foo == "abc" or not bar` });
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(`${SELECTORS.connector} .dropdown-toggle`)),
            ["any", "all"]
        );
        const tree = getTreeEditorContent(target);
        assert.deepEqual(tree, [
            { level: 0, value: "any" },
            { level: 1, value: "all" },
            { level: 2, value: "expr" },
            { level: 2, value: ["Foo", "=", "abc"] },
            { level: 1, value: ["Bar", "is", "not set"] },
        ]);
    });

    QUnit.test("rendering of connectors (2)", async (assert) => {
        await makeExpressionEditor({
            expression: `not (expr or foo == "abc")`,
            update(expression) {
                assert.step(expression);
            },
        });
        assert.strictEqual(
            target.querySelector(`${SELECTORS.connector} .dropdown-toggle`).textContent,
            "none"
        );
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "none" },
            { level: 1, value: "expr" },
            { level: 1, value: ["Foo", "=", "abc"] },
        ]);
        assert.verifySteps([]);
        assert.strictEqual(
            target.querySelector(SELECTORS.debugArea).value,
            `not (expr or foo == "abc")`
        );

        await selectConnector(target, "all");
        assert.strictEqual(
            target.querySelector(`${SELECTORS.connector} .dropdown-toggle`).textContent,
            "all"
        );
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "all" },
            { level: 1, value: "expr" },
            { level: 1, value: ["Foo", "=", "abc"] },
        ]);
        assert.verifySteps([`expr and foo == "abc"`]);
        assert.strictEqual(
            target.querySelector(SELECTORS.debugArea).value,
            `expr and foo == "abc"`
        );
    });

    QUnit.test("rendering of if else", async (assert) => {
        await makeExpressionEditor({ expression: `True if False else False` });
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "any" },
            { level: 1, value: "all" },
            { level: 2, value: ["0", "=", "1"] },
            { level: 2, value: ["1", "=", "1"] },
            { level: 1, value: "all" },
            { level: 2, value: ["1", "=", "1"] },
            { level: 2, value: ["0", "=", "1"] },
        ]);
    });

    QUnit.test("check condition by default when creating a new rule", async (assert) => {
        patchWithCleanup(odoo, { debug: false });
        serverData.models.partner.fields.country_id = { string: "Country ID", type: "char" };
        await makeExpressionEditor({ expression: "expr" });
        await click(target, "a[role='button']");
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "all" },
            { level: 1, value: "expr" },
            { level: 1, value: ["Country ID", "=", ""] },
        ]);
    });

    QUnit.test("allow selection of boolean field", async (assert) => {
        await makeExpressionEditor({ expression: "id" });
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "all" },
            { level: 1, value: ["ID", "is set"] },
        ]);
        await openModelFieldSelectorPopover(target);
        await click(target.querySelector(".o_model_field_selector_popover_item_name"));
        assert.deepEqual(getTreeEditorContent(target), [
            { level: 0, value: "all" },
            { level: 1, value: ["Bar", "is", "set"] },
        ]);
    });

    QUnit.test("render false and true leaves", async (assert) => {
        await makeExpressionEditor({ expression: `False and True` });
        assert.deepEqual(getOperatorOptions(target), ["="]);
        assert.deepEqual(getValueOptions(target), ["1"]);
        assert.deepEqual(getOperatorOptions(target, -1), ["="]);
        assert.deepEqual(getValueOptions(target, -1), ["1"]);
    });

    QUnit.test("no field of type properties in model field selector", async (assert) => {
        patchWithCleanup(odoo, { debug: false });
        serverData.models.partner.fields.properties = {
            string: "Properties",
            type: "properties",
            definition_record: "product_id",
            definition_record_field: "definitions",
            searchable: true,
        };
        serverData.models.product.fields.definitions = {
            string: "Definitions",
            type: "properties_definition",
        };

        await makeExpressionEditor({
            expression: `properties`,
            fields: Object.fromEntries(
                Object.entries(serverData.models.partner.fields).filter(([name]) =>
                    ["bar", "foo", "properties"].includes(name)
                )
            ),
            update(expression) {
                assert.step(expression);
            },
        });
        assert.deepEqual(getTreeEditorContent(target), [
            {
                level: 0,
                value: "all",
            },
            {
                level: 1,
                value: ["Properties", "is set"],
            },
        ]);
        assert.ok(isNotSupportedPath(target));

        await clearNotSupported(target);
        assert.verifySteps([`foo == ""`]);

        await openModelFieldSelectorPopover(target);
        assert.deepEqual(
            getNodesTextContent([
                ...target.querySelectorAll(".o_model_field_selector_popover_item_name"),
            ]),
            ["Bar", "Foo"]
        );
    });

    QUnit.test("between operator", async (assert) => {
        await makeExpressionEditor({
            expression: `id == 1`,
            update(expression) {
                assert.step(expression);
            },
        });
        assert.deepEqual(getOperatorOptions(target), [
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
        assert.verifySteps([]);
        await selectOperator(target, "between");
        assert.verifySteps([`id >= 1 and id <= 1`]);
    });
});
