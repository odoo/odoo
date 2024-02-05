/** @odoo-module alias=@web/../tests/core/dropdown_accordion_item_tests default=false */

import { Component, xml } from "@odoo/owl";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { mountInFixture } from "@web/../tests/helpers/mount_in_fixture";
import {
    click,
    getFixture,
    mount,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("popover", popoverService);
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("Dropdown Accordion Item");

    QUnit.test("accordion can be rendered", async (assert) => {
        class Parent extends Component {
            static template = xml`<AccordionItem description="'Test'" class="'text-primary'" selected="false"><h5>In accordion</h5></AccordionItem>`;
            static components = { AccordionItem };
            static props = ["*"];
        }
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsOnce(target, "div.o_accordion");
        assert.containsOnce(target, ".o_accordion button.o_accordion_toggle");
        assert.containsNone(target, ".o_accordion_values");

        await click(target, "button.o_accordion_toggle");
        assert.containsOnce(target, ".o_accordion_values");
        assert.strictEqual(
            target.querySelector(".o_accordion_values").innerHTML,
            `<h5>In accordion</h5>`
        );
    });

    QUnit.test("dropdown with accordion keyboard navigation", async (assert) => {
        class Parent extends Component {
            static template = xml`
                <Dropdown>
                    <button>dropdown</button>
                    <t t-set-slot="content">
                        <DropdownItem>item 1</DropdownItem>
                        <AccordionItem description="'item 2'" selected="false">
                            <DropdownItem>item 2-1</DropdownItem>
                            <DropdownItem>item 2-2</DropdownItem>
                        </AccordionItem>
                        <DropdownItem>item 3</DropdownItem>
                    </t>
                </Dropdown>
            `;
            static components = { Dropdown, DropdownItem, AccordionItem };
            static props = ["*"];
        }

        env = await makeTestEnv();
        await mountInFixture(Parent, target, { env });
        await click(target, ".o-dropdown.dropdown-toggle");

        // Navigate with arrows
        assert.containsNone(
            target,
            ".dropdown-menu > .focus",
            "menu should not have any active items"
        );

        const scenarioSteps = [
            { key: "arrowdown", expected: "item 1" },
            { key: "arrowdown", expected: "item 2" },
            { key: "arrowdown", expected: "item 3" },
            { key: "arrowdown", expected: "item 1" },
            { key: "tab", expected: "item 2" },
            { key: "enter", expected: "item 2" },
            { key: "tab", expected: "item 2-1" },
            { key: "tab", expected: "item 2-2" },
            { key: "tab", expected: "item 3" },
            { key: "tab", expected: "item 1" },
            { key: "arrowup", expected: "item 3" },
            { key: "arrowup", expected: "item 2-2" },
            { key: "arrowup", expected: "item 2-1" },
            { key: "arrowup", expected: "item 2" },
            { key: "enter", expected: "item 2" },
            { key: "arrowup", expected: "item 1" },
            { key: "shift+tab", expected: "item 3" },
            { key: "shift+tab", expected: "item 2" },
            { key: "shift+tab", expected: "item 1" },
            { key: "end", expected: "item 3" },
            { key: "home", expected: "item 1" },
        ];

        for (let i = 0; i < scenarioSteps.length; i++) {
            const step = scenarioSteps[i];
            triggerHotkey(step.key);
            await nextTick();
            assert.strictEqual(
                target.querySelector(".dropdown-menu .focus").innerText,
                step.expected,
                `Step ${i}: selected menu should be ${step.expected}`
            );
            assert.strictEqual(
                document.activeElement.innerText,
                step.expected,
                `Step ${i}: document.activeElement should be ${step.expected}`
            );
        }
    });
});
