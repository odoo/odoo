// @ts-check

import { expect, test } from "@odoo/hoot";
import { click, hover, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { getDropdownMenu, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownGroup } from "@web/components/dropdown/dropdown_group";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";

const DROPDOWN_MENU = ".o-dropdown--menu.dropdown-menu";

test.tags("desktop");
test("DropdownGroup: when one Dropdown is open, others with same group name can be toggled on mouse-enter", async () => {
    expect.assertions(16);
    const beforeOpenProm = new Deferred();

    class Parent extends Component {
        static components = { Dropdown, DropdownGroup };
        /** @type {string[]} */
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

    await click(queryOne(".one"));
    await animationFrame();

    expect.verifySteps([]);
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".one").toHaveClass("show");

    await hover(".two");
    await animationFrame();
    expect.verifySteps(["beforeOpen"]);
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-two").toHaveCount(0);

    beforeOpenProm.resolve();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-two").toHaveCount(1);

    await hover(".three");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-three").toHaveCount(1);

    expect(".menu-four").toHaveCount(0);
    await hover(".four");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".menu-three").toHaveCount(1);
    expect(".menu-four").toHaveCount(0);

    await click("div.outside");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

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
        /** @type {string[]} */
        static props = [];
    }
    await mountWithCleanup(Parent);
    await click(".one");
    await animationFrame();
    expect(getDropdownMenu(".one")).toHaveCount(1);

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
        /** @type {string[]} */
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
    await click(".two");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(".one");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await hover(".two");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".two-menu").toHaveCount(0);
});

test.tags("desktop");
test("DropdownGroup: toggler focused on mouseenter", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup };
        /** @type {string[]} */
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

    await click("button.one");
    await animationFrame();
    expect("button.one").toBeFocused();
    expect(DROPDOWN_MENU).toHaveText("One Content");

    await hover("button.two");
    await animationFrame();
    expect("button.two").toBeFocused();
    expect(DROPDOWN_MENU).toHaveText("Two Content");
});

test.tags("desktop");
test("DropdownGroup: keyboard close returns focus to the toggler, not <body>", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup, DropdownItem };
        /** @type {string[]} */
        static props = [];
        static template = xml`
            <DropdownGroup>
                <Dropdown>
                    <button class="one">One</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'item-one'">Item One</DropdownItem>
                    </t>
                </Dropdown>
                <Dropdown>
                    <button class="two">Two</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'item-two'">Item Two</DropdownItem>
                    </t>
                </Dropdown>
            </DropdownGroup>
        `;
    }
    await mountWithCleanup(Parent);

    await click("button.one");
    await animationFrame();
    expect("button.one").toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(".item-one").toBeFocused();

    await press("Escape");
    await animationFrame();
    expect("button.one").toBeFocused();
});

test.tags("desktop");
test("DropdownGroup: a changed group name moves its dropdowns to the new group", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup, DropdownItem };
        static template = xml`
            <div class="away">away</div>
            <DropdownGroup group="this.state.groupA">
                <Dropdown>
                    <button class="one">one</button>
                    <t t-set-slot="content"><DropdownItem>c1</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>
            <DropdownGroup group="this.state.groupB">
                <Dropdown>
                    <button class="two">two</button>
                    <t t-set-slot="content"><DropdownItem>c2</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>`;
        /** @type {string[]} */
        static props = [];

        /** @type {{ groupA: string, groupB: string }} */
        state;

        setup() {
            this.state = useState({ groupA: "g1", groupB: "g2" });
        }
    }
    const parent = await mountWithCleanup(Parent);

    await click("button.one");
    await animationFrame();
    await hover("button.two");
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["c1"]);

    parent.state.groupB = "g1";
    await animationFrame();
    await hover(".away");
    await hover("button.two");
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["c2"]);
});

test.tags("desktop");
test("DropdownGroup: a dropdown mounted after a group move joins the new group", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup, DropdownItem };
        static template = xml`
            <div class="away">away</div>
            <DropdownGroup group="'gx'">
                <Dropdown>
                    <button class="one">one</button>
                    <t t-set-slot="content"><DropdownItem>c1</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>
            <DropdownGroup group="this.state.g">
                <Dropdown t-if="this.state.show">
                    <button class="two">two</button>
                    <t t-set-slot="content"><DropdownItem>c2</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>`;
        /** @type {string[]} */
        static props = [];

        /** @type {{ g: string, show: boolean }} */
        state;

        setup() {
            this.state = useState({ g: "gy", show: false });
        }
    }
    const parent = await mountWithCleanup(Parent);
    parent.state.g = "gx";
    await animationFrame();
    parent.state.show = true;
    await animationFrame();

    await click("button.one");
    await animationFrame();
    await hover(".away");
    await hover("button.two");
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["c2"]);
});

test.tags("desktop");
test("DropdownGroup: leaving a group while open stops the peers taking over", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup, DropdownItem };
        static template = xml`
            <div class="away">away</div>
            <DropdownGroup group="'ga'">
                <Dropdown>
                    <button class="one">one</button>
                    <t t-set-slot="content"><DropdownItem>c1</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>
            <DropdownGroup group="this.state.g">
                <Dropdown>
                    <button class="two">two</button>
                    <t t-set-slot="content"><DropdownItem>c2</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>`;
        /** @type {string[]} */
        static props = [];

        /** @type {{ g: string }} */
        state;

        setup() {
            this.state = useState({ g: "ga" });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click("button.two");
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["c2"]);

    parent.state.g = "gz";
    await animationFrame();
    await hover(".away");
    await hover("button.one");
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["c2"]);
});

test.tags("desktop");
test("DropdownGroup: unmounting one group leaves the others sharing its id intact", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup, DropdownItem };
        static template = xml`
            <div class="away">away</div>
            <DropdownGroup group="'gs'">
                <Dropdown>
                    <button class="one">one</button>
                    <t t-set-slot="content"><DropdownItem>c1</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>
            <DropdownGroup group="'gs'">
                <Dropdown>
                    <button class="two">two</button>
                    <t t-set-slot="content"><DropdownItem>c2</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>
            <DropdownGroup t-if="this.state.third" group="'gs'">
                <Dropdown>
                    <button class="three">three</button>
                    <t t-set-slot="content"><DropdownItem>c3</DropdownItem></t>
                </Dropdown>
            </DropdownGroup>`;
        /** @type {string[]} */
        static props = [];

        /** @type {{ third: boolean }} */
        state;

        setup() {
            this.state = useState({ third: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    parent.state.third = false;
    await animationFrame();

    await click("button.one");
    await animationFrame();
    await hover(".away");
    await hover("button.two");
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["c2"]);
});
