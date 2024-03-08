import { expect, test } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Component, useRef, xml } from "@odoo/owl";

import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

test("action can be prevented", async () => {
    registry.category("services").add(
        "action",
        {
            start() {
                return {
                    doActionButton() {
                        expect.step("doActionButton");
                    },
                };
            },
        },
        { force: true }
    );

    let executeInHook;
    let executeInHandler;

    class MyComponent extends Component {
        static template = xml`<div t-ref="root" t-on-click="onClick" class="myComponent">Some text</div>`;
        static props = ["*"];
        setup() {
            const rootRef = useRef("root");
            useViewButtons({}, rootRef, {
                beforeExecuteAction: () => {
                    expect.step("beforeExecuteAction in hook");
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
                expect.step("beforeExecuteAction on handler");
                return executeInHandler;
            };
            this.env.onClickViewButton({ beforeExecute, getResParams, clickParams });
        }
    }

    await mountWithCleanup(MyComponent);
    await contains(".myComponent").click();
    expect([
        "beforeExecuteAction on handler",
        "beforeExecuteAction in hook",
        "doActionButton",
    ]).toVerifySteps();

    executeInHook = false;
    await contains(".myComponent").click();
    expect(["beforeExecuteAction on handler", "beforeExecuteAction in hook"]).toVerifySteps();

    executeInHandler = false;
    await contains(".myComponent").click();
    expect(["beforeExecuteAction on handler"]).toVerifySteps();
});

test("ViewButton clicked in Dropdown close the Dropdown", async () => {
    registry.category("services").add(
        "action",
        {
            start() {
                return {
                    doActionButton() {
                        expect.step("doActionButton");
                    },
                };
            },
        },
        { force: true }
    );

    class MyComponent extends Component {
        static components = { Dropdown, DropdownItem, ViewButton };
        static template = xml`
            <div t-ref="root" class="myComponent">
                <Dropdown>
                    <button>dropdown</button>
                    <DropdownItem>
                        <ViewButton tag="'a'" clickParams="{ type:'action' }" string="'coucou'" record="{ resId: 1 }" />
                    </DropdownItem>
                </Dropdown>
            </div>
        `;
        static props = ["*"];
        setup() {
            const rootRef = useRef("root");
            useViewButtons({}, rootRef);
        }
    }

    await mountWithCleanup(MyComponent);
    await contains(".dropdown-toggle").click();
    expect(".dropdown-menu").toHaveCount(1);

    await contains("a[type=action]").click();
    expect(["doActionButton"]).toVerifySteps();
    expect(".dropdown-menu").toHaveCount(0);
});
