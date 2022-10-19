/** @odoo-module */
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { setupViewRegistries } from "./helpers";
import { click, getFixture, mount } from "../helpers/utils";
import { makeTestEnv } from "../helpers/mock_env";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { useRef, Component, xml } from "@odoo/owl";

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
                const getResParams = () => ({
                    resIds: [3],
                    resId: 3,
                });
                const clickParams = {};
                const beforeExecute = () => {
                    assert.step("beforeExecuteAction on handler");
                    return executeInHandler;
                };
                this.env.onClickViewButton({ beforeExecute, getResParams, clickParams });
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

    QUnit.test("ViewButton clicked in Dropdown close the Dropdown", async (assert) => {
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

        class MyComponent extends Component {
            setup() {
                const rootRef = useRef("root");
                useViewButtons({}, rootRef);
            }
        }
        MyComponent.components = { Dropdown, DropdownItem, ViewButton };
        MyComponent.template = xml`
            <div t-ref="root" class="myComponent">
                <Dropdown>
                    <t t-set-slot="toggler">dropdown</t>
                    <DropdownItem>
                        <ViewButton tag="'a'" clickParams="{ type:'action' }" string="'coucou'" record="{ resId: 1 }" />
                    </DropdownItem>
                </Dropdown>
            </div>
        `;

        const env = await makeTestEnv();
        await mount(MyComponent, target, { env });

        await click(target, ".dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");

        await click(target, "a[type=action]");
        assert.verifySteps(["doActionButton"]);
        assert.containsNone(target, ".dropdown-menu");
    });
});
