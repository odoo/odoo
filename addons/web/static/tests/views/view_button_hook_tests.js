/** @odoo-module */
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { setupViewRegistries } from "./helpers";
import { click, getFixture } from "../helpers/utils";
import { makeTestEnv } from "../helpers/mock_env";
import { registry } from "@web/core/registry";

const { useRef, mount, Component, xml } = owl;

QUnit.module("UseViewButton tests", (hooks) => {
    let target;
    hooks.beforeEach(() => {
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("action can be prevented", async (assert) => {
        registry.category("services").add(
            "action",
            {
                start() {
                    return {
                        doActionButton() {
                            assert.step("doActionButton");
                        },
                    };
                },
            },
            { force: true }
        );

        let executeInHook;
        let executeInHandler;
        class MyComponent extends Component {
            setup() {
                const rootRef = useRef("root");
                useViewButtons({}, rootRef, {
                    beforeExecuteAction: () => {
                        assert.step("beforeExecuteAction in hook");
                        return executeInHook;
                    },
                });
            }

            onClick() {
                const record = {
                    resIds: [3],
                    resId: 3,
                    load: () => {},
                };
                const clickParams = {};
                const beforeExecute = () => {
                    assert.step("beforeExecuteAction on handler");
                    return executeInHandler;
                };
                this.env.onClickViewButton({ beforeExecute, record, clickParams });
            }
        }
        MyComponent.template = xml`<div t-ref="root" t-on-click="onClick" class="myComponent">Some text</div>`;

        const env = await makeTestEnv();
        await mount(MyComponent, target, { env, props: {} });

        await click(target, ".myComponent");
        assert.verifySteps([
            "beforeExecuteAction on handler",
            "beforeExecuteAction in hook",
            "doActionButton",
        ]);

        executeInHook = false;
        await click(target, ".myComponent");
        assert.verifySteps(["beforeExecuteAction on handler", "beforeExecuteAction in hook"]);

        executeInHandler = false;
        await click(target, ".myComponent");
        assert.verifySteps(["beforeExecuteAction on handler"]);
    });
});
