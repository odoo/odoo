/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import {
    click,
    getFixture,
    mount,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../helpers/utils";

const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("Dropdown Accordion Item");

    QUnit.test("accordion can be rendered", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`<AccordionItem description="'Test'" class="'text-primary'" selected="false"><h5>In accordion</h5></AccordionItem>`;
        Parent.components = { AccordionItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.querySelector(".o_accordion").outerHTML,
            `<div class="o_accordion position-relative"><button class="o_menu_item o_accordion_toggle dropdown-item text-primary" tabindex="0" aria-expanded="false">Test</button></div>`
        );
        assert.containsOnce(target, "button.o_accordion_toggle");
        assert.containsNone(target, ".o_accordion_values");

        await click(target, "button.o_accordion_toggle");
        assert.containsOnce(target, ".o_accordion_values");
        assert.strictEqual(
            target.querySelector(".o_accordion_values").innerHTML,
            `<h5>In accordion</h5>`
        );
    });

    QUnit.test("dropdown with accordion keyboard navigation", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
            <Dropdown>
                <DropdownItem>item 1</DropdownItem>
                <AccordionItem description="'item 2'" selected="false">
                    <DropdownItem>item 2-1</DropdownItem>
                    <DropdownItem>item 2-2</DropdownItem>
                </AccordionItem>
                <DropdownItem>item 3</DropdownItem>
            </Dropdown>
        `;
        Parent.components = { Dropdown, DropdownItem, AccordionItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, ".o-dropdown .dropdown-toggle");

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

        for (const step of scenarioSteps) {
            triggerHotkey(step.key);
            await nextTick();
            assert.strictEqual(
                target.querySelector(".dropdown-menu .focus").innerText,
                step.expected,
                `selected menu should be ${step.expected}`
            );
            assert.strictEqual(
                document.activeElement.innerText,
                step.expected,
                `document.activeElement should be ${step.expected}`
            );
        }
    });
});
