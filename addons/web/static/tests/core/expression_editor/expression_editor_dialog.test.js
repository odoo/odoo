import { expect, test, describe } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    mountWithCleanup,
    makeDialogMockEnv,
    mockService,
} from "@web/../tests/web_test_helpers";
import {
    Country,
    Partner,
    Player,
    Product,
    Stage,
    Team,
    getTreeEditorContent,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";

import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";

describe.current.tags("desktop");

async function makeExpressionEditorDialog(params = {}) {
    const props = { ...params };

    class Parent extends Component {
        static components = { ExpressionEditorDialog };
        static template = xml`<ExpressionEditorDialog t-props="expressionEditorProps"/>`;
        static props = ["*"];
        setup() {
            this.expressionEditorProps = {
                expression: "1",
                close: () => {},
                onConfirm: () => {},
                ...props,
                resModel: "partner",
            };
            this.expressionEditorProps.fields = Partner._fields;
        }
        async set(expression) {
            this.expressionEditorProps.expression = expression;
            this.render();
            await animationFrame();
        }
    }
    const env = await makeDialogMockEnv();
    return mountWithCleanup(Parent, { env, props });
}

defineModels([Partner, Product, Team, Player, Country, Stage]);

test("expr well sent, onConfirm and onClose", async () => {
    const expression = `foo == 'batestr' and bar == True`;
    await makeExpressionEditorDialog({
        expression,
        close: () => {
            expect.step("close");
        },
        onConfirm: (result) => {
            expect.step(result);
        },
    });
    expect(".o_technical_modal").toHaveCount(1);
    await contains(".o_dialog footer button").click();
    expect.verifySteps([expression, "close"]);
});

test("expr well sent but wrong, so notification when onConfirm", async () => {
    const expression = `foo == 'bar' and bar = True`;
    mockService("notification", {
        add(message, options) {
            expect(message).toBe("Expression is invalid. Please correct it");
            expect(options).toEqual({ type: "danger" });
            expect.step("notification");
        },
    });
    await makeExpressionEditorDialog({
        expression,
    });
    expect(".o_technical_modal").toHaveCount(1);
    await contains(".modal-footer button").click();
    await contains(".modal-body button").click();
    expect(getTreeEditorContent()).toEqual([{ level: 0, value: "all" }]);
    expect.verifySteps(["notification"]);
});
