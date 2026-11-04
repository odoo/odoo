import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";

import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const DROPDOWN_TOGGLE = ".o-dropdown.dropdown-toggle";
const DROPDOWN_MENU = ".o-dropdown--menu.dropdown-menu";
const DROPDOWN_ITEM = ".o-dropdown-item.dropdown-item:not(.o-dropdown)";

test("can be rendered as <span/>", async () => {
    class Parent extends Component {
        static components = { DropdownItem };
        static props = [];
        static template = xml`<DropdownItem>coucou</DropdownItem>`;
    }
    await mountWithCleanup(Parent);

    expect(".dropdown-item").toHaveClass(["o-dropdown-item", "o-navigable", "dropdown-item"]);
    expect(".dropdown-item").toHaveAttribute("role", "menuitem");
});

test("(with href prop) can be rendered as <a/>", async () => {
    class Parent extends Component {
        static components = { DropdownItem };
        static props = [];
        static template = xml`<DropdownItem attrs="{ href: '#' }">coucou</DropdownItem>`;
    }
    await mountWithCleanup(Parent);
    expect(DROPDOWN_ITEM).toHaveAttribute("href", "#");
});

test("prevents click default with href", async () => {
    expect.assertions(4);
    // A DropdownItem should preventDefault a click as it may take the shape
    // of an <a/> tag with an [href] attribute and e.g. could change the url when clicked.
    patchWithCleanup(DropdownItem.prototype, {
        onClick(ev) {
            expect(!ev.defaultPrevented).toBe(true);
            super.onClick(...arguments);
            const href = ev.target.getAttribute("href");
            // defaultPrevented only if props.href is defined
            expect(href !== null ? ev.defaultPrevented : !ev.defaultPrevented).toBe(true);
        },
    });
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button>Coucou</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'link'" attrs="{href: '#'}"/>
                        <DropdownItem class="'nolink'" />
                    </t>
                </Dropdown>`;
    }
    await mountWithCleanup(Parent);
    // The item containing the link class contains an href prop,
    // which will turn it into <a href=> So it must be defaultPrevented
    // The other one not contain any href props, it must not be defaultPrevented,
    // so as not to prevent the background change flow for example
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    await click(".link");
    await click("button.dropdown-toggle");
    await click(".nolink");
});

test("can be styled", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown menuClass="'test-menu'">
                    <button class="test-toggler">Coucou</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'test-dropdown-item'">Item</DropdownItem>
                    </t>
                </Dropdown>
            `;
    }

    await mountWithCleanup(Parent);
    expect(DROPDOWN_TOGGLE).toHaveClass("test-toggler");

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass("test-menu");
    expect(DROPDOWN_ITEM).toHaveClass("test-dropdown-item");
});
