import { test, expect } from "@odoo/hoot";
import { click, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

test("accordion can be rendered", async () => {
    class Parent extends Component {
        static template = xml`<AccordionItem description="'Test'" class="'text-primary'" selected="false"><h5>In accordion</h5></AccordionItem>`;
        static components = { AccordionItem };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect("div.o_accordion").toHaveCount(1);
    expect(".o_accordion button.o_accordion_toggle").toHaveCount(1);
    expect(".o_accordion_values").toHaveCount(0);

    await click("button.o_accordion_toggle");
    await animationFrame();
    expect(".o_accordion_values").toHaveCount(1);
    expect(queryOne(".o_accordion_values").innerHTML).toBe(`<h5>In accordion</h5>`);
});

test("dropdown with accordion keyboard navigation", async () => {
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

    await mountWithCleanup(Parent);
    await click(".o-dropdown.dropdown-toggle");
    await animationFrame();

    expect(".dropdown-menu > .focus").toHaveCount(0);

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
        await press(step.key);
        await animationFrame();
        await runAllTimers();
        expect(`.dropdown-menu .focus:contains(${step.expected})`).toBeFocused();
    }
});
