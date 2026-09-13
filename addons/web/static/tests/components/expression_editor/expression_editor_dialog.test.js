// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    Country,
    getTreeEditorContent,
    Partner,
    Player,
    Product,
    Stage,
    Team,
} from "@web/../tests/components/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    makeDialogMockEnv,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { ExpressionEditorDialog } from "@web/components/expression_editor_dialog/expression_editor_dialog";

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
                fields: Partner._fields,
            };
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
            return () => {};
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

test("a value edited during validation is not confirmed using the old validation", async () => {
    const validation = new Deferred();
    patchWithCleanup(ExpressionEditorDialog.prototype, {
        isValueValid() {
            expect.step(`validate:${this.state.value}`);
            return validation;
        },
    });
    const dialog = await mountWithCleanup(ExpressionEditorDialog, {
        env: await makeDialogMockEnv(),
        props: {
            expression: "1",
            resModel: "partner",
            fields: Partner._fields,
            onConfirm: (value) => expect.step(`confirm:${value}`),
            close: () => expect.step("close"),
        },
    });
    const confirmation = dialog.onConfirm();
    dialog.update("2");
    validation.resolve(true);
    await confirmation;
    expect.verifySteps(["validate:1"]);
    await dialog.onConfirm();
    expect.verifySteps(["validate:2", "confirm:2", "close"]);
});

for (const outcome of ["resolve", "reject"]) {
    test(`confirmation stays pending until its callback can ${outcome}`, async () => {
        const saved = new Deferred();
        saved.catch(() => {});
        let attempts = 0;
        const dialog = await mountWithCleanup(ExpressionEditorDialog, {
            env: await makeDialogMockEnv(),
            props: {
                expression: "1",
                resModel: "partner",
                fields: Partner._fields,
                onConfirm: () => {
                    attempts++;
                    return saved;
                },
                close: () => expect.step("close"),
            },
        });
        const result = /** @type {{ failure?: Error }} */ ({});
        const pending = dialog.onConfirm().catch((error) => {
            result.failure = error;
        });
        await animationFrame();
        expect(".modal-footer .btn-primary").toHaveAttribute("disabled");
        await dialog.onConfirm();
        expect(attempts).toBe(1);
        expect.verifySteps([]);
        const error = new Error("save rejected");
        if (outcome === "reject") {
            saved.reject(error);
        } else {
            saved.resolve();
        }
        await pending;
        await animationFrame();
        expect(result.failure).toBe(outcome === "reject" ? error : undefined);
        expect(".modal-footer .btn-primary").not.toHaveAttribute("disabled");
        expect.verifySteps(outcome === "reject" ? [] : ["close"]);
    });
}
