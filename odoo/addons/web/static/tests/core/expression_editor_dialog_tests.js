/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { makeDialogTestEnv } from "../helpers/mock_env";
import { mount, getFixture, nextTick, click } from "../helpers/utils";
import {
    getTreeEditorContent,
    makeServerData,
    setupConditionTreeEditorServices,
} from "./condition_tree_editor_helpers";
import { registry } from "@web/core/registry";

/**
 * @typedef {Record<keyof DomainSelectorDialog.props, any>} Props
 */

/**
 * @param {Partial<Props> & { mockRPC: Function }} [params]
 */
async function makeExpressionEditorDialog(params = {}) {
    const props = { ...params };
    const mockRPC = props.mockRPC;
    delete props.mockRPC;

    class Parent extends Component {
        static components = { ExpressionEditorDialog };
        static template = xml`<ExpressionEditorDialog t-props="expressionEditorProps"/>`;
        setup() {
            this.expressionEditorProps = {
                resModel: "partner",
                expression: "1",
                close: () => {},
                onConfirm: () => {},
                ...props,
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

    const env = await makeDialogTestEnv({ serverData, mockRPC });
    return mount(Parent, target, { env, props });
}

/** @type {Element} */
let target;
let serverData;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = makeServerData();
        setupConditionTreeEditorServices();
        target = getFixture();
    });

    QUnit.module("ExpressionEditorDialog");

    QUnit.test("expr well sent, onConfirm and onClose", async (assert) => {
        const expression = `foo == 'batestr' and bar == True`;
        await makeExpressionEditorDialog({
            expression,
            close: () => {
                assert.step("close");
            },
            onConfirm: (result) => {
                assert.step(result);
            },
        });
        assert.containsOnce(target, ".o_technical_modal");
        const confirmButton = target.querySelector(".o_dialog footer button");
        await click(confirmButton);
        assert.verifySteps([expression, "close"]);
    });

    QUnit.test("expr well sent but wrong, so notification when onConfirm", async (assert) => {
        const expression = `foo == 'bar' and bar = True`;
        registry.category("services").add(
            "notification",
            {
                start() {
                    return {
                        add(message, options) {
                            assert.strictEqual(message, "Expression is invalid. Please correct it");
                            assert.deepEqual(options, { type: "danger" });
                            assert.step("notification");
                        },
                    };
                },
            },
            { force: true }
        );
        await makeExpressionEditorDialog({
            expression,
        });
        assert.containsOnce(target, ".o_technical_modal");
        const confirmButton = target.querySelector(".modal-footer button");
        const resetButton = target.querySelector(".modal-body button");
        await click(confirmButton);
        await click(resetButton);
        assert.deepEqual(getTreeEditorContent(target), [{ level: 0, value: "all" }]);
        assert.verifySteps(["notification"]);
    });
});
