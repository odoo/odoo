// @ts-check

import { expect, getFixture, test } from "@odoo/hoot";
import {
    click,
    hover,
    keyDown,
    leave,
    pointerDown,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    resize,
} from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers, tick } from "@odoo/hoot-mock";
import { Component, onMounted, onPatched, useRef, useState, xml } from "@odoo/owl";
import { getPickerCell } from "@web/../tests/components/datetime/datetime_test_helpers";
import {
    contains,
    defineParams,
    getMockEnv,
    makeMockEnv,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { DateTimeInput } from "@web/components/datetime/datetime_input";
import { CheckboxItem } from "@web/components/dropdown/checkbox_item";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownGroup } from "@web/components/dropdown/dropdown_group";
import { useDropdownState } from "@web/components/dropdown/dropdown_hook";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { Dialog } from "@web/ui/dialog/dialog";
import { Popover } from "@web/ui/popover/popover";

const DROPDOWN_TOGGLE = ".o-dropdown.dropdown-toggle";
const DROPDOWN_MENU = ".o-dropdown--menu.dropdown-menu";
const DROPDOWN_ITEM = ".o-dropdown-item.dropdown-item:not(.o-dropdown)";

class SimpleDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = xml`
        <div class="outside">outside</div>
        <Dropdown t-props="this.dropdownProps">
            <button>Dropdown</button>
            <t t-set-slot="content">
                <DropdownItem class="'item-a'">Item A</DropdownItem>
                <DropdownItem class="'item-b'">Item B</DropdownItem>
                <DropdownItem class="'item-c'">Item C</DropdownItem>
            </t>
        </Dropdown>
    `;
}

class MultiLevelDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = xml`
        <div class="outside">outside</div>
        <Dropdown t-props="this.dropdownProps">
            <button class="dropdown-a">A</button>
            <t t-set-slot="content">
                <DropdownItem class="'item-a'">Item A</DropdownItem>
                <Dropdown t-props="this.dropdownProps">
                    <button class="dropdown-b">B</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'item-b'">Item B</DropdownItem>
                        <Dropdown t-props="this.dropdownProps">
                            <button class="dropdown-c">C</button>
                            <t t-set-slot="content">
                                <DropdownItem class="'item-c'">Item C</DropdownItem>
                            </t>
                        </Dropdown>
                    </t>
                </Dropdown>
            </t>
        </Dropdown>
    `;
}

class NoBottomSheetDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = xml`
        <Dropdown t-props="this.dropdownProps" bottomSheet="false">
            <button>Dropdown</button>
            <t t-set-slot="content">
                <DropdownItem class="'item-a'">Item A</DropdownItem>
            </t>
        </Dropdown>
    `;
}

function startOpenState() {
    const state = useState({
        isOpen: true,
        open: () => {
            state.isOpen = true;
        },
        close: () => {
            state.isOpen = false;
        },
    });
    return state;
}

test("can be rendered", async () => {
    await mountWithCleanup(SimpleDropdown);

    expect(DROPDOWN_TOGGLE).toHaveCount(1);
    expect(DROPDOWN_MENU).toHaveCount(0);

    expect(DROPDOWN_TOGGLE).toHaveClass(["o-dropdown", "dropdown-toggle", "dropdown"]);
    expect(DROPDOWN_TOGGLE).toHaveAttribute("aria-expanded", "false");
});

test("items prop validates each item's shape", async () => {
    class Parent extends Component {
        static components = { Dropdown };
        static props = ["*"];
        static template = xml`
            <Dropdown items="[{ label: 'X' }]">
                <button>Dropdown</button>
            </Dropdown>
        `;
    }
    expect.errors(1);
    await expect(mountWithCleanup(Parent)).rejects.toThrow(
        /Invalid props for component 'Dropdown'/,
    );
    await animationFrame();
    expect.verifyErrors([/Invalid props for component 'Dropdown'/]);
});

test("can be toggled", async () => {
    const beforeOpenProm = new Deferred();
    class Parent extends SimpleDropdown {
        setup() {
            this.dropdownProps = {
                beforeOpen: () => {
                    expect.step("beforeOpen");
                    return beforeOpenProm;
                },
            };
        }
    }

    await mountWithCleanup(Parent);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect.verifySteps(["beforeOpen"]);
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect(DROPDOWN_TOGGLE).toHaveAttribute("aria-expanded", "false");
    beforeOpenProm.resolve();
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(DROPDOWN_MENU).toHaveAttribute("role", "menu");
    expect(DROPDOWN_TOGGLE).toHaveAttribute("aria-expanded", "true");

    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_handle_bar");
    } else {
        await click(DROPDOWN_TOGGLE);
    }
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect(DROPDOWN_TOGGLE).toHaveAttribute("aria-expanded", "false");
});

test("initial open state can be true", async () => {
    class Parent extends SimpleDropdown {
        setup() {
            this.dropdownProps = {
                state: startOpenState(),
            };
        }
    }

    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(1);
});

test("close on outside click", async () => {
    await mountWithCleanup(SimpleDropdown);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_backdrop");
    } else {
        await click("div.outside");
    }
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test("close on outside click in shadow dom", async () => {
    class DropdownInShadowDom extends Component {
        static components = { SimpleDropdown };
        static props = [];
        static template = xml`<div><SimpleDropdown/></div>`;
    }

    class ShadowDom extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`<div class="shadow-root" t-ref="shadow-root-ref" />`;
        setup() {
            const shadowRootRef = useRef("shadow-root-ref");
            onMounted(() => {
                const shadowBody = shadowRootRef.el.attachShadow({ mode: "open" });
                mountWithCleanup(DropdownInShadowDom, { target: shadowBody });
            });
        }
    }

    await mountWithCleanup(ShadowDom, { noMainContainer: true });

    const shadowBody = queryOne(".shadow-root").shadowRoot;
    await contains(DROPDOWN_TOGGLE, { root: shadowBody }).click();
    await animationFrame();
    expect(queryAll(DROPDOWN_MENU, { root: shadowBody })).toHaveCount(1);

    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_backdrop", { root: shadowBody });
    } else {
        await click(".outside", { root: shadowBody });
    }
    await animationFrame();
    expect(queryAll(DROPDOWN_MENU, { root: shadowBody })).toHaveCount(0);
});

test("close on item selection", async () => {
    await mountWithCleanup(SimpleDropdown);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(DROPDOWN_ITEM);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test.tags("desktop");
test("hold position on hover", async () => {
    patchWithCleanup(Popover.prototype, {
        onPositioned(el, solution) {
            this.shouldAnimate = false;
            super.onPositioned(el, solution);
        },
    });

    /** @type {{ filler: boolean; }} */
    let parentState;
    class Parent extends Component {
        setup() {
            this.state = useState({ filler: false });
            parentState = this.state;
        }
        static template = xml`
            <div t-if="this.state.filler" class="filler" style="height: 100px;"/>
            <Dropdown holdOnHover="true">
                <button>Hello</button>
                <t t-set-slot="content">World</t>
            </Dropdown>
        `;
        static components = { Dropdown };
        static props = [];
    }

    await mountWithCleanup(Parent);
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    const menuBox1 = queryOne(DROPDOWN_MENU).getBoundingClientRect();

    await hover(DROPDOWN_MENU);

    expect(".filler").toHaveCount(0);
    parentState.filler = true;
    await animationFrame();

    expect(".filler").toHaveCount(1);
    const menuBox2 = queryOne(DROPDOWN_MENU).getBoundingClientRect();
    expect(menuBox2.top - menuBox1.top).toBe(0);

    await leave();

    const menuBox3 = queryOne(DROPDOWN_MENU).getBoundingClientRect();
    expect(menuBox3.top - menuBox1.top).toBe(100);
});

test("unlock position after close", async () => {
    class Parent extends Component {
        static template = xml`
                <div style="margin-left: 200px;">
                    <Dropdown holdOnHover="true" position="'bottom-end'">
                        <button></button>
                    </Dropdown>
                </div>
            `;
        static components = { Dropdown };
        static props = [];
    }
    await mountWithCleanup(Parent);
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    const menuBox1 = queryOne(DROPDOWN_MENU).getBoundingClientRect();

    await hover(DROPDOWN_MENU);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    const menuBox2 = queryOne(DROPDOWN_MENU).getBoundingClientRect();
    expect(menuBox2.left - menuBox1.left).toBe(0);
});

test.tags("desktop");
test("dropdowns keynav", async () => {
    expect.assertions(39);

    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button data-hotkey="m">Toggle</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'item1'" onSelected="() => this.onItemSelected(1)">item1</DropdownItem>
                        <DropdownItem class="'item2'" attrs="{'data-hotkey': '2'}" onSelected="() => this.onItemSelected(2)">item2</DropdownItem>
                        <DropdownItem class="'item3'" onSelected="() => this.onItemSelected(3)">item3</DropdownItem>
                    </t>
                </Dropdown>
            `;
        onItemSelected(value) {
            expect.step(value.toString());
        }
    }

    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0);

    await press("alt+m");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    expect(".dropdown-menu > .focus").toHaveCount(0);

    const scenarioSteps = [
        { hotkey: "arrowdown", expected: "item1" },
        { hotkey: "arrowdown", expected: "item2" },
        { hotkey: "arrowdown", expected: "item3" },
        { hotkey: "arrowdown", expected: "item1" },
        { hotkey: "tab", expected: "item2" },
        { hotkey: "tab", expected: "item3" },
        { hotkey: "tab", expected: "item1" },
        { hotkey: "arrowup", expected: "item3" },
        { hotkey: "arrowup", expected: "item2" },
        { hotkey: "arrowup", expected: "item1" },
        { hotkey: "shift+tab", expected: "item3" },
        { hotkey: "shift+tab", expected: "item2" },
        { hotkey: "shift+tab", expected: "item1" },
        { hotkey: "end", expected: "item3" },
        { hotkey: "home", expected: "item1" },
    ];

    for (let i = 0; i < scenarioSteps.length; i++) {
        const step = scenarioSteps[i];
        await press(step.hotkey);
        await tick();
        await animationFrame();

        expect(".dropdown-menu > .focus").toHaveClass(step.expected, {
            message: `Matches the class ".${step.expected}" on step ${i}`,
        });
        expect(".dropdown-menu > .focus").toBeFocused();
    }

    await press("enter");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    await press("alt+m");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await press("alt+2");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    await press("alt+m");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await press("escape");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    expect.verifySteps(["1", "2"]);
});

test.tags("desktop");
test("dropdowns keynav is not impacted by bootstrap", async () => {
    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
                <Dropdown state="this.dropdown">
                    <button>Open</button>
                    <t t-set-slot="content">
                        <select><option>foo</option></select>
                    </t>
                </Dropdown>
            `;

        setup() {
            this.dropdown = startOpenState();
        }
    }
    await mountWithCleanup(Parent);
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(1);

    expect(DROPDOWN_MENU).toHaveClass("o-dropdown--menu");

    await pointerDown("select");

    await keyDown("ArrowDown");
    await animationFrame();

    await keyDown("Escape");
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(0);
});

test.tags("desktop");
test("refocus toggler on close with keynav", async () => {
    await mountWithCleanup(SimpleDropdown);
    expect(DROPDOWN_TOGGLE).not.toBeFocused();

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_TOGGLE).toBeFocused();

    await press("ArrowDown");
    await animationFrame();
    expect(".dropdown-item:first-child").toBeFocused();

    await press("Escape");
    await animationFrame();
    expect(DROPDOWN_TOGGLE).toBeFocused();
});

test.tags("desktop");
test("opening a dropdown over another restores focus to its own toggler", async () => {
    /** @type {Parent} */
    let parent;
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
            <Dropdown state="this.stateA">
                <button class="toggler-a">A</button>
                <t t-set-slot="content">
                    <DropdownItem class="'item-a'">Item A</DropdownItem>
                </t>
            </Dropdown>
            <Dropdown state="this.stateB">
                <button class="toggler-b">B</button>
                <t t-set-slot="content">
                    <DropdownItem class="'item-b'">Item B</DropdownItem>
                </t>
            </Dropdown>
        `;
        setup() {
            this.stateA = useDropdownState();
            this.stateB = useDropdownState();
            parent = this;
        }
    }
    await mountWithCleanup(Parent);

    queryOne(".toggler-a").focus();
    parent.stateA.open();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".toggler-a").toBeFocused();

    parent.stateB.open();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expect(".toggler-b").toBeFocused();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test.tags("desktop");
test("programmatic close does not steal focus from an editable outside the dropdown", async () => {
    class DropdownWithOutsideInput extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
            <input class="outside-input"/>
            <Dropdown state="this.dropdownState">
                <button>Dropdown</button>
                <t t-set-slot="content">
                    <DropdownItem class="'item-a'">Item A</DropdownItem>
                </t>
            </Dropdown>
        `;
        setup() {
            this.dropdownState = useDropdownState();
        }
    }
    const comp = await mountWithCleanup(DropdownWithOutsideInput);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(DROPDOWN_TOGGLE).toBeFocused();

    queryOne("input.outside-input").focus();
    expect("input.outside-input").toBeFocused();

    comp.dropdownState.close();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect("input.outside-input").toBeFocused();
});

test.tags("desktop");
test("closing with focus on an editable inside the dropdown refocuses the toggler", async () => {
    class DropdownWithInsideInput extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
            <Dropdown state="this.dropdownState">
                <button>Dropdown</button>
                <t t-set-slot="content">
                    <input class="inside-input"/>
                </t>
            </Dropdown>
        `;
        setup() {
            this.dropdownState = useDropdownState();
        }
    }
    const comp = await mountWithCleanup(DropdownWithInsideInput);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    queryOne("input.inside-input").focus();
    expect("input.inside-input").toBeFocused();

    comp.dropdownState.close();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect(DROPDOWN_TOGGLE).toBeFocused();
});

test.tags("desktop");
test("navigationProps changes navigation behaviour", async () => {
    class Parent extends SimpleDropdown {
        setup() {
            this.dropdownProps = {
                navigationOptions: {
                    virtualFocus: true,
                    hotkeys: {
                        arrowup: () => expect.step("arrowup"),
                    },
                },
            };
        }
    }

    await mountWithCleanup(Parent);
    await click(DROPDOWN_TOGGLE);
    await animationFrame();

    expect(DROPDOWN_TOGGLE).toBeFocused();
    expect(".o-dropdown-item:nth-child(1)").not.toHaveClass("focus");

    await press("arrowdown");

    expect(DROPDOWN_TOGGLE).toBeFocused();
    expect(".o-dropdown-item:nth-child(1)").toHaveClass("focus");

    expect.verifySteps([]);

    await press("arrowup");

    expect(DROPDOWN_TOGGLE).toBeFocused();
    expect(".o-dropdown-item:nth-child(1)").toHaveClass("focus");
    expect.verifySteps(["arrowup"]);
});

test("'o-dropdown-caret' class adds a caret", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button class="first o-dropdown-caret">First</button>
                    <t t-set-slot="content">
                        <DropdownItem>Item</DropdownItem>
                        <Dropdown>
                            <button class="second">Second</button>
                            <t t-set-slot="content">
                                <DropdownItem>Item</DropdownItem>
                            </t>
                        </Dropdown>
                        <Dropdown>
                            <button class="third o-dropdown--no-caret">Third</button>
                            <t t-set-slot="content">
                                <DropdownItem>Item</DropdownItem>
                            </t>
                        </Dropdown>
                    </t>
                </Dropdown>
            `;
    }
    await mountWithCleanup(Parent);

    const getContent = (selector) => {
        const element = queryOne(selector);
        const styles = window.getComputedStyle(element, "::after");
        return styles.content;
    };

    expect(getContent(".first")).not.toBe("none");

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(getContent(".second")).not.toBe("none");
    expect(getContent(".third")).toBe("none");
});

test.tags("desktop");
test("direction class set to default when closed", async () => {
    await resize({ height: 600 });

    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
            <Dropdown>
                <!-- style dropdown to be at the bottom to force popover to position on top -->
                <button class="o-dropdown-caret" style="margin-top: 500px">First</button>
                <t t-set-slot="content">
                    <div style="height: 300px"/>
                    Content
                </t>
            </Dropdown>
        `;
    }

    await mountWithCleanup(Parent);
    expect(DROPDOWN_TOGGLE).not.toHaveClass("show");
    expect(DROPDOWN_TOGGLE).toHaveClass("dropdown");

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_TOGGLE).toHaveClass("show");
    expect(DROPDOWN_TOGGLE).toHaveClass("dropup");

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_TOGGLE).not.toHaveClass("show");
    expect(DROPDOWN_TOGGLE).toHaveClass("dropdown");
});

test.tags("desktop");
test("tooltip on toggler", async () => {
    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button data-tooltip="My tooltip">Dropdown toggler</button>
                    <t t-set-slot="content">
                        Hello
                    </t>
                </Dropdown>
            `;
    }

    await mountWithCleanup(Parent);
    expect(DROPDOWN_TOGGLE).toHaveAttribute("data-tooltip", "My tooltip");

    await hover(DROPDOWN_TOGGLE);
    await runAllTimers();
    expect(".o-tooltip").toHaveText("My tooltip");
});

test("date picker inside does not close when a click occurs in date picker", async () => {
    class Parent extends Component {
        static components = { DateTimeInput, Dropdown };
        static props = [];
        static template = xml`
                    <Dropdown>
                        <button>Dropdown toggler</button>
                        <t t-set-slot="content">
                            <DateTimeInput />
                        </t>
                    </Dropdown>
                `;
    }

    await mountWithCleanup(Parent);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(0);
    expect(".o_datetime_input").toHaveValue("");

    await click(".o_datetime_input");
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(1);
    expect(".o_datetime_input").toHaveValue("");

    await click(getPickerCell("15"));
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(1);
    expect(".o_datetime_input").not.toHaveValue("");
});

test("onOpened callback props called after the menu has been mounted", async () => {
    const beforeOpenProm = new Deferred();

    class Parent extends SimpleDropdown {
        setup() {
            this.dropdownProps = {
                beforeOpen: () => {
                    expect.step("beforeOpened");
                    return beforeOpenProm;
                },
                onOpened: () => {
                    expect.step("onOpened");
                },
            };
        }
    }
    await mountWithCleanup(Parent);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();

    expect.verifySteps(["beforeOpened"]);
    beforeOpenProm.resolve();
    await animationFrame();

    expect.verifySteps(["onOpened"]);
});

test("dropdown button can be disabled", async () => {
    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button disabled="">Open</button>
                    <t t-set-slot="content">
                        Coucou
                    </t>
                </Dropdown>
            `;
    }
    await mountWithCleanup(Parent);
    expect(DROPDOWN_TOGGLE).toHaveProperty("disabled", true);
});

test("Dropdown with CheckboxItem: toggle value", async () => {
    class Parent extends Component {
        static template = xml`
                <Dropdown>
                    <button>Click to open</button>
                    <t t-set-slot="content">
                        <CheckboxItem
                            class="{ selected: this.state.checked }"
                            checked="this.state.checked"
                            closingMode="'none'"
                            onSelected.bind="this.onSelected">
                            My checkbox item
                        </CheckboxItem>
                    </t>
                </Dropdown>`;
        static components = { Dropdown, CheckboxItem };
        static props = [];
        setup() {
            this.state = useState({ checked: false });
        }
        onSelected() {
            this.state.checked = !this.state.checked;
        }
    }
    await mountWithCleanup(Parent);
    await click(DROPDOWN_TOGGLE);
    await animationFrame();

    expect(DROPDOWN_ITEM).toHaveAttribute("aria-checked", "false");
    expect(DROPDOWN_ITEM).not.toHaveClass(["selected", "focus"]);

    await click(DROPDOWN_ITEM);
    await animationFrame();
    expect(DROPDOWN_ITEM).toHaveAttribute("aria-checked", "true");
    expect(DROPDOWN_ITEM).toHaveClass(["selected", "focus"]);
});

test("don't close dropdown outside the active element", async () => {
    const env = await makeMockEnv();

    class CustomDialog extends Component {
        static components = { Dialog, Dropdown, DropdownItem };
        static props = { close: true };
        static template = xml`
                <Dialog title="'Welcome'">
                    <Dropdown>
                        <button class="dialog-toggle">Dropdown</button>
                        <t t-set-slot="content">
                            <DropdownItem class="'dialog-item'">Item</DropdownItem>
                        </t>
                    </Dropdown>
                    <div class="outside-dialog">Outside Dialog</div>
                </Dialog>
            `;
    }

    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
                <div>
                    <Dropdown>
                        <button class="parent-toggle">Dropdown</button>
                        <t t-set-slot="content">
                            <button class="parent-item" t-on-click="this.clicked">Click me</button>
                        </t>
                    </Dropdown>
                    <div class="outside-parent">Outside Parent</div>
                </div>
            `;

        clicked() {
            env.services.dialog.add(CustomDialog);
        }
    }

    await mountWithCleanup(Parent, { env });

    await click("button.parent-toggle");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    await click("button.parent-item");
    await animationFrame();
    expect(".modal-dialog").toHaveCount(1);

    await click(".modal-dialog button.dialog-toggle");
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(2);
    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_backdrop");
    } else {
        await click(".outside-dialog");
    }
    await click(".outside-dialog");
    await animationFrame();
    expect(".modal-dialog").toHaveCount(1);
    expect(DROPDOWN_MENU).toHaveCount(1);

    if (getMockEnv().isSmall) {
        await click(".modal-dialog .oi-arrow-left");
    } else {
        await click(".modal-dialog .btn-close");
    }
    await animationFrame();
    expect(".modal-dialog").toHaveCount(0);
    expect(DROPDOWN_MENU).toHaveCount(1);
    await click(".outside-parent");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test("t-if t-else as toggler", async () => {
    /** @type {{foo: string}} */
    let state;

    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button t-if="this.state.foo === 'bar'">Coucou</button>
                    <a t-else="">ByeBye</a>
                    <t t-set-slot="content">
                        Hello
                    </t>
                </Dropdown>
            `;

        setup() {
            state = useState({ foo: "bar" });
            this.state = state;
        }
    }
    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    state.foo = "boo";
    await animationFrame();
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
});

test("Dropdown in dialog in dropdown, first dropdown should stay open when clicking inside the second one", async () => {
    const env = await makeMockEnv();

    class DialogDropdown extends Component {
        static components = { Dialog, Dropdown };
        static props = { close: true };
        static template = xml`
                <Dialog>
                    <button class="inside-dialog">Inside Dialog</button>
                    <Dropdown>
                        <button class="dialog-dropdown">Open</button>
                        <t t-set-slot="content">
                            <button class="dialog-button">Coucou</button>
                        </t>
                    </Dropdown>
                </Dialog>
            `;
    }

    class Parent extends Component {
        static components = { Dropdown };
        static props = {};
        static template = xml`
                <Dropdown>
                    <button class="root-dropdown">Coucou</button>
                    <t t-set-slot="content">
                        <button t-on-click="() => this.onClick()" class="root-button">Open Dialog</button>
                    </t>
                </Dropdown>
            `;

        onClick() {
            env.services.dialog.add(DialogDropdown);
        }
    }

    await mountWithCleanup(Parent, { env });
    expect(DROPDOWN_MENU).toHaveCount(0);

    await click(".root-dropdown");
    await animationFrame();
    await click(".root-button");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(".dialog-dropdown");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    await click(".dialog-button");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_backdrop");
    } else {
        await click(".inside-dialog");
    }
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
});

test("multi-level dropdown: can be rendered and toggled", async () => {
    await mountWithCleanup(MultiLevelDropdown);

    await click(".dropdown-a");
    await animationFrame();

    await click(".dropdown-b");
    await animationFrame();

    await click(".dropdown-c");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(3);
});

test("multi-level dropdown: initial open state can be true", async () => {
    class Parent extends MultiLevelDropdown {
        setup() {
            this.dropdownProps = {
                state: useState({
                    isOpen: true,
                    open: () => {},
                    close: () => {},
                }),
            };
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();
    await animationFrame();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(3);
});

test("multi-level dropdown: close on outside click", async () => {
    await mountWithCleanup(MultiLevelDropdown);

    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();
    await click(".dropdown-c");
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(3);
    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_backdrop");
        await animationFrame();
        await click(".o_bottom_sheet_backdrop");
        await animationFrame();
        await click(".o_bottom_sheet_backdrop");
    } else {
        await click("div.outside");
    }
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test("multi-level dropdown: close on item selection", async () => {
    await mountWithCleanup(MultiLevelDropdown);

    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();

    expect(DROPDOWN_MENU).toHaveCount(2);
    expect(DROPDOWN_ITEM).toHaveCount(2);

    await click(".o-dropdown-item.item-b");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test("multi-level dropdown: parent closing modes on item selection", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <div class="outside">outside</div>
                <Dropdown>
                    <button class="dropdown-a">Dropdown A</button>
                    <t t-set-slot="content">
                        <Dropdown>
                            <button class="dropdown-b">Dropdown B</button>
                            <t t-set-slot="content">
                                <DropdownItem class="'item1'" closingMode="'none'">A</DropdownItem>
                                <DropdownItem class="'item2'" closingMode="'closest'">B</DropdownItem>
                                <DropdownItem class="'item3'" closingMode="'all'">C</DropdownItem>
                                <DropdownItem class="'item4'">D</DropdownItem>
                            </t>
                        </Dropdown>
                    </t>
                </Dropdown>
            `;
    }
    await mountWithCleanup(Parent);

    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();

    await click(".item1");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    await click(".item2");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(".dropdown-b");
    await animationFrame();

    await click(".item3");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();

    await click(".item4");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test("multi-level dropdown: recursive template can be rendered", async () => {
    class Parent extends Component {
        static template = "recursive.Template";
        static props = [];
        static components = { Dropdown, DropdownItem };
        setup() {
            this.dropdown = startOpenState();

            this.name = "foo";
            this.items = [
                {
                    name: "foo-0",
                    children: [
                        { name: "foo-00", children: [] },
                        {
                            name: "foo-01",
                            children: [
                                { name: "foo-010", children: [] },
                                { name: "foo-011", children: [] },
                                {
                                    name: "foo-012",
                                    children: [
                                        { name: "foo-0120", children: [] },
                                        { name: "foo-0121", children: [] },
                                        { name: "foo-0122", children: [] },
                                    ],
                                },
                            ],
                        },
                        { name: "foo-02", children: [] },
                    ],
                },
                { name: "foo-1", children: [] },
                { name: "foo-2", children: [] },
            ];
        }
    }

    await mountWithCleanup(Parent, {
        templates: {
            ["recursive.Template"]: `
                <Dropdown state="dropdown">
                    <button><t t-esc="name" /></button>
                    <t t-set-slot="content">
                        <t t-foreach="items" t-as="item" t-key="item_index">

                            <t t-if="!item.children.length">
                                <DropdownItem><t t-esc="item.name"/></DropdownItem>
                            </t>

                            <t t-else="" t-call="recursive.Template">
                                <t t-set="name" t-value="item.name" />
                                <t t-set="items" t-value="item.children" />
                            </t>
                        </t>
                    </t>
                </Dropdown>
            `,
        },
    });

    await animationFrame();
    await animationFrame();
    await animationFrame();
    await animationFrame();

    expect(queryAllTexts(".dropdown-toggle, .dropdown-menu > .dropdown-item")).toEqual([
        "foo",
        "foo-0",
        "foo-1",
        "foo-2",
        "foo-00",
        "foo-01",
        "foo-02",
        "foo-010",
        "foo-011",
        "foo-012",
        "foo-0120",
        "foo-0121",
        "foo-0122",
    ]);
});

test.tags("desktop");
test("multi-level dropdown: keynav", async () => {
    expect.assertions(211);
    class Parent extends Component {
        onItemSelected(value) {
            expect.step(value);
        }
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button class="first" data-hotkey="1">First</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'first-first'" onSelected="() => this.onItemSelected('first-first')">O</DropdownItem>
                        <Dropdown>
                            <button class="second">Second</button>
                            <t t-set-slot="content">
                                <DropdownItem class="'second-first'" onSelected="() => this.onItemSelected('second-first')">O</DropdownItem>
                                <Dropdown>
                                    <button class="third">Third</button>
                                    <t t-set-slot="content">
                                        <DropdownItem class="'third-first'" onSelected="() => this.onItemSelected('third-first')">O</DropdownItem>
                                        <DropdownItem class="'third-last'" onSelected="() => this.onItemSelected('third-last')">O</DropdownItem>
                                    </t>
                                </Dropdown>
                                <DropdownItem class="'second-last'" onSelected="() => this.onItemSelected('second-last')">O</DropdownItem>
                            </t>
                        </Dropdown>
                        <DropdownItem class="'first-last'" onSelected="() => this.onItemSelected('first-last')">O</DropdownItem>
                    </t>
                </Dropdown>
            `;
    }
    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0, {
        message: "menus are closed at the start",
    });

    const scenarioSteps = [
        { hotkey: "alt+1" },
        { hotkey: "arrowup", highlighted: ["first-last"] },
        { hotkey: "arrowup", highlighted: ["second"] },
        { hotkey: "arrowdown", highlighted: ["first-last"] },
        { hotkey: "arrowdown", highlighted: ["first-first"] },
        { hotkey: "arrowdown", highlighted: ["second"] },
        { hotkey: "tab", highlighted: ["first-last"] },
        { hotkey: "tab", highlighted: ["first-first"] },
        { hotkey: "tab", highlighted: ["second"] },
        { hotkey: "shift+tab", highlighted: ["first-first"] },
        { hotkey: "shift+tab", highlighted: ["first-last"] },
        { hotkey: "shift+tab", highlighted: ["second"] },
        { hotkey: "arrowright", highlighted: ["second", "second-first"] },
        { hotkey: "arrowright", highlighted: ["second", "second-first"] },
        { hotkey: "arrowleft", highlighted: ["second"] },
        { hotkey: "arrowleft", highlighted: ["second"] },
        { hotkey: "arrowright", highlighted: ["second", "second-first"] },
        { hotkey: "arrowup", highlighted: ["second", "second-last"] },
        { hotkey: "arrowup", highlighted: ["second", "third"] },
        { hotkey: "arrowup", highlighted: ["second", "second-first"] },
        { hotkey: "arrowdown", highlighted: ["second", "third"] },
        { hotkey: "arrowright", highlighted: ["second", "third", "third-first"] },
        { hotkey: "arrowright", highlighted: ["second", "third", "third-first"] },
        { hotkey: "arrowleft", highlighted: ["second", "third"] },
        { hotkey: "arrowleft", highlighted: ["second"] },
        { hotkey: "arrowleft", highlighted: ["second"] },
        { hotkey: "arrowright", highlighted: ["second", "second-first"] },
        { hotkey: "arrowdown", highlighted: ["second", "third"] },
        { hotkey: "arrowright", highlighted: ["second", "third", "third-first"] },
        { hotkey: "arrowup", highlighted: ["second", "third", "third-last"] },
        { hotkey: "home", highlighted: ["second", "third", "third-first"] },
        { hotkey: "home", highlighted: ["second", "third", "third-first"] },
        { hotkey: "end", highlighted: ["second", "third", "third-last"] },
        { hotkey: "end", highlighted: ["second", "third", "third-last"] },
        { hotkey: "arrowleft", highlighted: ["second", "third"] },
        { hotkey: "enter", highlighted: ["second", "third", "third-first"] },
        { hotkey: "enter", selected: "third-first" },
        { hotkey: "alt+1" },
        { hotkey: "arrowup", highlighted: ["first-last"] },
        { hotkey: "arrowup", highlighted: ["second"] },
        { hotkey: "arrowright", highlighted: ["second", "second-first"] },
        { hotkey: "arrowup", highlighted: ["second", "second-last"] },
        { hotkey: "arrowup", highlighted: ["second", "third"] },
        { hotkey: "arrowright", highlighted: ["second", "third", "third-first"] },
        { hotkey: "escape", highlighted: ["second", "third"] },
        { hotkey: "escape", highlighted: ["second"] },
        { hotkey: "escape", highlighted: [] },
    ];

    for (const [stepIndex, step] of scenarioSteps.entries()) {
        await press(step.hotkey);
        await tick();
        await tick();
        await animationFrame();

        if (step.highlighted !== undefined) {
            const activeElements = queryAll(".focus");
            expect(activeElements).toHaveLength(step.highlighted.length, {
                message: `step ${stepIndex}: all active elements to check are found`,
            });

            for (let i = 0; i < activeElements.length; i++) {
                expect(activeElements[i]).toHaveClass(step.highlighted[i]);
            }

            const lastActiveElement = activeElements.slice(-1)[0];
            if (lastActiveElement) {
                expect(lastActiveElement).toHaveClass(step.highlighted.slice(-1)[0]);
                expect(
                    lastActiveElement.classList.contains("dropdown")
                        ? lastActiveElement.querySelector(":scope > .dropdown-toggle")
                        : lastActiveElement,
                ).toBeFocused();
            } else {
                expect(document.activeElement).toHaveClass("first");
            }
        }
        if (step.selected !== undefined) {
            const verify = [step.selected];
            expect.verifySteps(verify);
        }
    }
});

test.tags("desktop");
test("multi-level dropdown: keynav when rtl direction", async () => {
    expect.assertions(10);
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button class="first" data-hotkey="1">First</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'first-first'">O</DropdownItem>
                        <Dropdown>
                            <button class="second">Second</button>
                            <t t-set-slot="content">
                                <DropdownItem class="'second-first'">O</DropdownItem>
                            </t>
                        </Dropdown>
                    </t>
                </Dropdown>
            `;
    }

    defineParams({
        lang_parameters: {
            direction: "rtl",
        },
    });

    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0, {
        message: "menus are closed at the start",
    });

    const scenarioSteps = [
        { hotkey: "alt+1" },
        { hotkey: "arrowdown", highlighted: ["first-first"] },
        { hotkey: "arrowdown", highlighted: ["second"] },
        { hotkey: "arrowleft", highlighted: ["second", "second-first"] },
        { hotkey: "arrowright", highlighted: ["second"] },
    ];

    for (const [stepIndex, step] of scenarioSteps.entries()) {
        await press(step.hotkey);
        await animationFrame();
        if (step.highlighted !== undefined) {
            const activeElements = queryAll(".focus");
            expect(activeElements).toHaveLength(step.highlighted.length, {
                message: `step ${stepIndex}: all active elements to check are found`,
            });

            for (let i = 0; i < activeElements.length; i++) {
                expect(activeElements[i]).toHaveClass(step.highlighted[i]);
            }
        }
    }
});

test.tags("desktop");
test("multi-level dropdown: submenu keeps position when patched", async () => {
    expect.assertions(6);

    patchWithCleanup(Dropdown.prototype, {
        setup() {
            super.setup(...arguments);
            if (this.hasParent) {
                onMounted(() => {
                    expect.step(`submenu mounted`);
                });
                let previousMenuRect;
                onPatched(() => {
                    expect.step(`submenu patched`);
                    if (this.state.isOpen && this.menuRef.el) {
                        const subMenuRect = this.menuRef.el.getBoundingClientRect();
                        if (previousMenuRect) {
                            expect(subMenuRect.top).toBe(previousMenuRect.top);
                            expect(subMenuRect.left).toBe(previousMenuRect.left);
                        }
                        previousMenuRect = subMenuRect;
                    }
                });
            }
        },
    });

    /** @type {{ foo: boolean; }} */
    let parentState;
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button class="one">one</button>
                    <t t-set-slot="content">
                        <Dropdown>
                            <button class="two">two</button>
                            <t t-set-slot="content">
                                <DropdownItem t-if="this.state.foo" class="this.three">three</DropdownItem>
                            </t>
                        </Dropdown>
                    </t>
                </Dropdown>
            `;
        setup() {
            this.state = useState({ foo: false });
            parentState = this.state;
        }
    }

    await mountWithCleanup(Parent);
    expect.verifySteps([]);

    await click(".one");
    await animationFrame();
    expect.verifySteps(["submenu mounted"]);

    await click(".two");
    await animationFrame();
    parentState.foo = true;
    await animationFrame();
    expect.verifySteps(["submenu patched"]);

    parentState.foo = false;
    await animationFrame();
    expect.verifySteps(["submenu patched"]);
});

test.tags("desktop");
test("multi-level dropdown: mouseentering a dropdown item should close any subdropdown", async () => {
    expect.assertions(4);
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
                    <Dropdown>
                        <button class="main">Main</button>
                        <t t-set-slot="content">
                            <DropdownItem class="'item'">Item</DropdownItem>
                            <Dropdown>
                                <button class="sub">Sub</button>
                                <t t-set-slot="content">
                                    <DropdownItem class="'sub-item'">Sub Item</DropdownItem>
                                </t>
                            </Dropdown>
                        </t>
                    </Dropdown>
                `;
    }
    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0, {
        message: "menus are closed at the start",
    });

    await click(".main");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1, {
        message: "1st menu is opened",
    });

    await hover(".sub");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    await hover(".item");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1, {
        message: "only 1st menu is opened",
    });
});

test.tags("desktop");
test("multi-level dropdown: unsubscribe all keynav when root destroyed", async () => {
    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
            <Dropdown>
                <button class="first">First</button>
                <t t-set-slot="content">
                    <Dropdown>
                        <button class="second">Second</button>
                        <t t-set-slot="content">
                            <Dropdown>
                                <button class="third">Third</button>
                                <t t-set-slot="content">
                                    <p>Coucou</p>
                                </t>
                            </Dropdown>
                        </t>
                    </Dropdown>
                </t>
            </Dropdown>
        `;
    }

    const hotkeys = [
        "home",
        "end",
        "tab",
        "shift+tab",
        "arrowdown",
        "arrowup",
        "arrowleft",
        "arrowright",
        "escape",
        "enter",
    ];
    hotkeys.sort();

    const registeredHotkeys = new Set();
    const removedHotkeys = new Set();

    function checkKeys(keySet) {
        const sortedKeys = [...keySet];
        sortedKeys.sort();

        expect(sortedKeys).toEqual(hotkeys);
        keySet.clear();
    }

    await makeMockEnv();
    mockService("hotkey", {
        add(key) {
            const remove = super.add(...arguments);
            registeredHotkeys.add(key);
            return () => {
                remove();
                removedHotkeys.add(key);
            };
        },
    });

    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect(registeredHotkeys.size).toBe(0);

    await click(".first");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    checkKeys(registeredHotkeys);

    await hover(".second");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);
    checkKeys(registeredHotkeys);

    await hover(".third");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(3);

    await press("escape");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);
    checkKeys(removedHotkeys);

    await hover(getFixture());

    await hover(".third");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(3);
    checkKeys(registeredHotkeys);

    await press("escape");
    await animationFrame();

    await press("escape");
    await animationFrame();
    checkKeys(removedHotkeys);

    await press("escape");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
    checkKeys(removedHotkeys);
});

test.tags("mobile");
test("dropdown: no BottomSheet", async () => {
    await mountWithCleanup(NoBottomSheetDropdown);
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    expect(".o_bottom_sheet").toHaveCount(0);
});

test.tags("desktop");
test("a mouseenter on an open dropdown does not hijack focus on the next open", async () => {
    /** @type {ReturnType<typeof useDropdownState>} */
    let state;
    class Parent extends Component {
        static components = { Dropdown, DropdownGroup };
        static template = xml`
            <input class="decoy" type="text"/>
            <input class="realOwner" type="text"/>
            <DropdownGroup group="'g'">
                <Dropdown state="this.state">
                    <button class="toggler">Toggle</button>
                    <t t-set-slot="content"><button class="item">Item</button></t>
                </Dropdown>
            </DropdownGroup>`;
        static props = ["*"];
        setup() {
            this.state = state = useDropdownState();
        }
    }
    await mountWithCleanup(Parent);

    await click(".toggler");
    await animationFrame();
    queryOne(".decoy").focus();
    queryOne(".toggler").dispatchEvent(new MouseEvent("mouseenter"));

    state.close();
    await animationFrame();

    queryOne(".realOwner").focus();
    state.open();
    await animationFrame();

    queryOne(".item").focus();
    state.close();
    await animationFrame();

    expect(document.activeElement).toBe(queryOne(".realOwner"));
});

test("a toggler the slot stops rendering is left as it was found", async () => {
    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
            <Dropdown>
                <button t-if="this.state.primary" class="first">First</button>
                <button t-else="" class="second">Second</button>
                <t t-set-slot="content">Menu</t>
            </Dropdown>`;
        setup() {
            this.state = useState({ primary: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    const first = queryOne("button.first");
    expect(first).toHaveClass("o-dropdown");
    expect(first).toHaveAttribute("aria-expanded", "false");

    parent.state.primary = false;
    await animationFrame();
    expect(queryOne("button.second")).toHaveClass("o-dropdown");
    expect(first).not.toHaveClass("o-dropdown");
    expect(first).not.toHaveClass("dropdown");
    expect(first).not.toHaveAttribute("aria-expanded");
});

test.tags("desktop");
test("a dropdown that opens in the tick it mounts still closes its peers", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown state="this.a">
                <button class="a">a</button>
                <t t-set-slot="content"><DropdownItem>ca</DropdownItem></t>
            </Dropdown>
            <t t-if="this.state.showB">
                <Dropdown state="this.b">
                    <button class="b">b</button>
                    <t t-set-slot="content"><DropdownItem>cb</DropdownItem></t>
                </Dropdown>
            </t>`;
        static props = [];

        setup() {
            this.state = useState({ showB: false });
            this.a = useDropdownState();
            this.b = useDropdownState();
        }
    }
    const parent = await mountWithCleanup(Parent);
    parent.a.open();
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["ca"]);

    parent.state.showB = true;
    parent.b.open();
    await animationFrame();
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["cb"]);
});

test.tags("desktop");
test("an established dropdown closes an already-open peer", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown state="this.a">
                <button class="a">a</button>
                <t t-set-slot="content"><DropdownItem>ca</DropdownItem></t>
            </Dropdown>
            <Dropdown state="this.b">
                <button class="b">b</button>
                <t t-set-slot="content"><DropdownItem>cb</DropdownItem></t>
            </Dropdown>`;
        static props = [];

        setup() {
            this.a = useDropdownState();
            this.b = useDropdownState();
        }
    }
    const parent = await mountWithCleanup(Parent);
    parent.a.open();
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["ca"]);

    parent.b.open();
    await animationFrame();
    expect(queryAllTexts(DROPDOWN_MENU)).toEqual(["cb"]);
});

test.tags("desktop");
test("a menuClass that changes while the menu is open reaches it", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown menuClass="this.state.cls">
                <button class="tog">tog</button>
                <t t-set-slot="content"><DropdownItem>c</DropdownItem></t>
            </Dropdown>`;
        static props = [];

        setup() {
            this.state = useState({ cls: "aaa" });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click("button.tog");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass("aaa");

    parent.state.cls = "bbb";
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass("bbb");
    expect(DROPDOWN_MENU).not.toHaveClass("aaa");
    expect(DROPDOWN_MENU).toHaveClass("dropdown-menu");
});

test.tags("desktop");
test("an object menuClass is toggled off as well as on", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown menuClass="{ dark: this.state.dark, always: true }">
                <button class="tog">tog</button>
                <t t-set-slot="content"><DropdownItem>c</DropdownItem></t>
            </Dropdown>`;
        static props = [];

        setup() {
            this.state = useState({ dark: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click("button.tog");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass(["dark", "always"]);

    parent.state.dark = false;
    await animationFrame();
    expect(DROPDOWN_MENU).not.toHaveClass("dark");
    expect(DROPDOWN_MENU).toHaveClass("always");
});

test.tags("desktop");
test("a menuClass repeating a popover class cannot strip it", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown menuClass="this.state.cls">
                <button class="tog">tog</button>
                <t t-set-slot="content"><DropdownItem>c</DropdownItem></t>
            </Dropdown>`;
        static props = [];

        setup() {
            this.state = useState({ cls: "dropdown-menu extra" });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click("button.tog");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass(["dropdown-menu", "extra"]);

    parent.state.cls = "other";
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass(["dropdown-menu", "other"]);
    expect(DROPDOWN_MENU).not.toHaveClass("extra");
});

test.tags("desktop");
test("reopening after a menuClass change while closed uses the current one", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown menuClass="this.state.cls">
                <button class="tog">tog</button>
                <t t-set-slot="content"><DropdownItem>c</DropdownItem></t>
            </Dropdown>`;
        static props = [];

        setup() {
            this.state = useState({ cls: "aaa" });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click("button.tog");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass("aaa");
    await click("button.tog");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    parent.state.cls = "ccc";
    await animationFrame();
    await click("button.tog");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveClass("ccc");
    expect(DROPDOWN_MENU).not.toHaveClass("aaa");
});

test("multi-level dropdown: opening a grandchild leaves its ancestors open", async () => {
    await mountWithCleanup(MultiLevelDropdown);

    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();
    await click(".dropdown-c");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(3, {
        message: "A, B and C are all open: C is a grandchild of A, not a rival",
    });
});

test("an unrelated dropdown opening closes the open one", async () => {
    class Parent extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
            <Dropdown>
                <button class="dropdown-one">One</button>
                <t t-set-slot="content"><DropdownItem>Item one</DropdownItem></t>
            </Dropdown>
            <Dropdown>
                <button class="dropdown-two">Two</button>
                <t t-set-slot="content"><DropdownItem>Item two</DropdownItem></t>
            </Dropdown>`;
    }
    await mountWithCleanup(Parent);

    await click(".dropdown-one");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(".dropdown-two");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1, {
        message: "neither is an ancestor of the other, so the first gives way",
    });
});

test("a swapped `state` prop is refused rather than silently ignored", async () => {
    /** @type {Parent} */
    let parent;
    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
            <Dropdown state="this.state.which === 'a' ? this.stateA : this.stateB">
                <button class="toggler">toggle</button>
                <t t-set-slot="content"><div class="menu-body">menu</div></t>
            </Dropdown>`;
        setup() {
            this.stateA = useDropdownState();
            this.stateB = useDropdownState();
            this.state = useState({ which: "a" });
            parent = this;
        }
    }

    await mountWithCleanup(Parent);
    parent.stateA.open();
    await animationFrame();
    expect(".menu-body").toHaveCount(1);
    parent.stateA.close();
    await animationFrame();

    expect.errors(1);
    parent.state.which = "b";
    await animationFrame();
    expect.verifyErrors([/the `state` prop is read once/]);
});

test("an open menu is watched by one observer, however often the dropdown re-renders", async () => {
    let updates = 0;
    patchWithCleanup(Dropdown.prototype, {
        setup() {
            super.setup();
            const navigator = this.navigation;
            const update = navigator.update.bind(navigator);
            navigator.update = () => {
                updates++;
                return update();
            };
        },
    });
    class Parent extends Component {
        static props = ["*"];
        static components = { Dropdown, DropdownItem };
        static template = xml`
            <Dropdown>
                <button class="toggler">toggle</button>
                <t t-set-slot="content">
                    <t t-foreach="this.state.items" t-as="item" t-key="item">
                        <DropdownItem class="'item'" t-out="item"/>
                    </t>
                </t>
            </Dropdown>
        `;
        setup() {
            this.state = useState({ items: ["a", "b"] });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click(".toggler");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    parent.state.items.push("c");
    await animationFrame();
    await animationFrame();
    expect(DROPDOWN_ITEM).toHaveCount(3);

    const before = updates;
    queryOne(DROPDOWN_MENU).appendChild(document.createElement("span"));
    await animationFrame();
    expect(updates - before).toBe(1, {
        message:
            "one mutation, one navigation update, after a re-render of the open dropdown",
    });
});

test("an open menu follows the dropdown's later renders: slot fields and items", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Dropdown };
        static template = xml`
            <Dropdown items="this.items">
                <button class="toggler">toggle</button>
                <t t-set-slot="content">
                    <span class="plain" t-out="this.plain"/>
                </t>
            </Dropdown>
        `;
        plain = "first";
        items = [{ label: "one", onSelected: () => {} }];
        setup() {
            this.state = useState({ tick: 0 });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click(".toggler");
    await animationFrame();
    expect(".plain").toHaveText("first");
    expect(queryAllTexts(DROPDOWN_ITEM)).toEqual(["one"]);

    parent.plain = "second";
    parent.items = [...parent.items, { label: "two", onSelected: () => {} }];
    parent.state.tick++;
    await animationFrame();
    await animationFrame();
    expect(".plain").toHaveText("second", {
        message: "a plain field read by the content slot follows the parent's render",
    });
    expect(queryAllTexts(DROPDOWN_ITEM)).toEqual(["one", "two"], {
        message: "the items prop follows too",
    });
});

test("a closed dropdown syncs its popover once, at mount, not again at setup", async () => {
    let closes = 0;
    patchWithCleanup(Dropdown.prototype, {
        closePopover() {
            closes++;
            return super.closePopover();
        },
    });
    class Parent extends Component {
        static props = ["*"];
        static components = { Dropdown };
        static template = xml`<Dropdown><button class="toggler">toggle</button></Dropdown>`;
    }
    await mountWithCleanup(Parent);
    expect(closes).toBe(1);
    await click(".toggler");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);
    await click(".toggler");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect(closes).toBe(2);
});
