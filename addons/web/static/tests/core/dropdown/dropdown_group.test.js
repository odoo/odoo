import { expect, test } from "@odoo/hoot";
import { click, hover, queryOne } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";

import { getDropdownMenu, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";

const DROPDOWN_MENU = ".o-dropdown--menu.dropdown-menu";

test.tags("desktop");
test("DropdownGroup: when one Dropdown is open, others with same group name can be toggled on mouse-enter", async () => {
    expect.assertions(16);
    const beforeOpenProm = new Deferred();

    class Parent extends Component {
        static components = { Dropdown, DropdownGroup };
        static props = [];
        static template = xml`
                    <div>
                        <div class="outside">OUTSIDE</div>
                        <DropdownGroup>
                            <Dropdown menuClass="'menu-one'">
                                <button class="one">One</button>
                                <t t-set-slot="content">
                                    Content One
                                </t>
                            </Dropdown>
                            <Dropdown beforeOpen="() => this.beforeOpen()" menuClass="'menu-two'">
                                <button class="two">Two</button>
                                <t t-set-slot="content">
                                    Content Two
                                </t>
                            </Dropdown>
                            <Dropdown menuClass="'menu-three'">
                                <button class="three">Three</button>
                                <t t-set-slot="content">
                                    Content Three
                                </t>
                            </Dropdown>
                        </DropdownGroup>
                        <DropdownGroup>
                            <Dropdown menuClass="'menu-four'">
                                <button class="four">Four</button>
                                <t t-set-slot="content">
                                    Content Four
                                </t>
                            </Dropdown>
                        </DropdownGroup>
                    </div>
                `;

        beforeOpen() {
            expect.step("beforeOpen");
            return beforeOpenProm;
        }
    }
    await mountWithCleanup(Parent);

    // Click on ONE
    await click(queryOne(".one"));
    await animationFrame();

    expect.verifySteps([]);
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".one").toHaveClass("show");

    // Hover on TWO
    await hover(".two");
    await animationFrame();
    expect.verifySteps(["beforeOpen"]);
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-two").toHaveCount(0);

    beforeOpenProm.resolve();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-two").toHaveCount(1);

    // Hover on THREE
    await hover(".three");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-three").toHaveCount(1);

    // Hover on FOUR (Should not open)
    expect(".menu-four").toHaveCount(0);
    await hover(".four");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-three").toHaveCount(1);
    expect(".menu-four").toHaveCount(0);

    // Click on OUTSIDE
    await click("div.outside");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    // Hover on ONE, TWO, THREE
    await hover(".one");
    await hover(".two");
    await hover(".three");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test.tags("desktop");
test("DropdownGroup: when non-sibling Dropdown is open, other must not be toggled on mouse-enter", async () => {
    class Parent extends Component {
        static template = xml`
                    <div>
                        <DropdownGroup>
                            <Dropdown>
                                <button class="one">One</button>
                                <t t-set-slot="content">One Content</t>
                            </Dropdown>
                        </DropdownGroup>
                        <DropdownGroup>
                            <Dropdown>
                                <button class="two">Two</button>
                                <t t-set-slot="content">Two Content</t>
                            </Dropdown>
                        </DropdownGroup>
                    </div>
                `;
        static components = { Dropdown, DropdownGroup };
        static props = [];
    }
    await mountWithCleanup(Parent);
    // Click on One
    await click(".one");
    await animationFrame();
    expect(getDropdownMenu(".one")).toHaveCount(1);

    // Hover on Two
    await hover(".two");
    await animationFrame();
    expect(getDropdownMenu(".one")).toHaveCount(1);

    expect(".one").toHaveClass("show");
    expect(".two").not.toHaveClass("show");
});

test.tags("desktop");
test("DropdownGroup: when one is open, then non-sibling toggled, siblings must not be toggled on mouse-enter", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup };
        static props = [];
        static template = xml`
                    <div>
                        <DropdownGroup>
                            <Dropdown>
                                <button class="one">One</button>
                                <t t-set-slot="content">
                                    One Content
                                </t>
                            </Dropdown>
                        </DropdownGroup>
                        <DropdownGroup>
                            <Dropdown>
                                <button class="two">Two</button>
                                <t t-set-slot="content">
                                    Two Content
                                </t>
                            </Dropdown>
                        </DropdownGroup>
                    </div>
                `;
    }
    await mountWithCleanup(Parent);
    // Click on BAR1
    await click(".two");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Click on FOO
    await click(".one");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Hover on BAR1
    await hover(".two");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".two-menu").toHaveCount(0);
});

test.tags("desktop");
test("DropdownGroup: toggler focused on mouseenter", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup };
        static props = [];
        static template = xml`
            <DropdownGroup>
                <Dropdown>
                    <button class="one">One</button>
                    <t t-set-slot="content">
                        One Content
                    </t>
                </Dropdown>
                <Dropdown>
                    <button class="two">Two</button>
                    <t t-set-slot="content">
                        Two Content
                    </t>
                </Dropdown>
            </DropdownGroup>
        `;
    }
    await mountWithCleanup(Parent);

    // Click on one
    await click("button.one");
    await animationFrame();
    expect("button.one").toBeFocused();
    expect(DROPDOWN_MENU).toHaveText("One Content");

    // Hover on two
    await hover("button.two");
    await animationFrame();
    expect("button.two").toBeFocused();
    expect(DROPDOWN_MENU).toHaveText("Two Content");
});
