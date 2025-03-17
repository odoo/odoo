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
import { Deferred, animationFrame, runAllTimers, tick } from "@odoo/hoot-mock";
import { Component, onMounted, onPatched, useState, xml } from "@odoo/owl";

import { makeMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import { defineParams, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dialog } from "@web/core/dialog/dialog";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const DROPDOWN_TOGGLE = ".o-dropdown.dropdown-toggle";
const DROPDOWN_MENU = ".o-dropdown--menu.dropdown-menu";
const DROPDOWN_ITEM = ".o-dropdown-item.dropdown-item:not(.o-dropdown)";

class SimpleDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [];
    static template = xml`
        <div class="outside">outside</div>
        <Dropdown t-props="dropdownProps">
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
        <Dropdown t-props="dropdownProps">
            <button class="dropdown-a">A</button>
            <t t-set-slot="content">
                <DropdownItem class="'item-a'">Item A</DropdownItem>
                <Dropdown t-props="dropdownProps">
                    <button class="dropdown-b">B</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'item-b'">Item B</DropdownItem>
                        <Dropdown t-props="dropdownProps">
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

    await click(DROPDOWN_TOGGLE);
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

    await click("div.outside");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
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
    // Disable popover animations for this test
    patchWithCleanup(Popover.prototype, {
        onPositioned(el, solution) {
            this.shouldAnimate = false;
            super.onPositioned(el, solution);
        },
    });

    let parentState;
    class Parent extends Component {
        setup() {
            this.state = useState({ filler: false });
            parentState = this.state;
        }
        static template = xml`
            <div t-if="state.filler" class="filler" style="height: 100px;"/>
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

    // Pointer enter the dropdown menu
    await hover(DROPDOWN_MENU);

    // Add a filler to the parent
    expect(".filler").toHaveCount(0);
    parentState.filler = true;
    await animationFrame();

    expect(".filler").toHaveCount(1);
    const menuBox2 = queryOne(DROPDOWN_MENU).getBoundingClientRect();
    expect(menuBox2.top - menuBox1.top).toBe(0);

    // Pointer leave the dropdown menu
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

    // Pointer enter the dropdown menu to lock the menu
    await hover(DROPDOWN_MENU);

    // close the menu
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    // and reopen it
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
                        <DropdownItem class="'item1'" onSelected="() => onItemSelected(1)">item1</DropdownItem>
                        <DropdownItem class="'item2'" attrs="{'data-hotkey': '2'}" onSelected="() => onItemSelected(2)">item2</DropdownItem>
                        <DropdownItem class="'item3'" onSelected="() => onItemSelected(3)">item3</DropdownItem>
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

    // Select last one activated in previous scenario (item1)
    await press("enter");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    // Reopen dropdown
    await press("alt+m");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Select second item through data-hotkey attribute
    await press("alt+2");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    // Reopen dropdown
    await press("alt+m");
    await tick();
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Close dropdown with keynav
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
                <Dropdown state="dropdown">
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

    // This class presence makes bootstrap ignore the below event
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

    // Toggler is focused, no focus in dropdown
    expect(DROPDOWN_TOGGLE).toBeFocused();
    expect(".o-dropdown-item:nth-child(1)").not.toHaveClass("focus");

    // After arrow down, toggler is still focused, virtual focus in dropdown
    await press("arrowdown");

    expect(DROPDOWN_TOGGLE).toBeFocused();
    expect(".o-dropdown-item:nth-child(1)").toHaveClass("focus");

    expect.verifySteps([]);

    // Arrow up is overridden, nothing should change
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

    // Check that the "::after" pseudo-element is NOT empty, there is a caret
    expect(getContent(".first")).not.toBe("none");

    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    // Check that the "::after" pseudo-element is NOT empty, there is a caret
    expect(getContent(".second")).not.toBe("none");
    // Check that the "::after" pseudo-element is empty,there are not caret
    expect(getContent(".third")).toBe("none");
});

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

    // open
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_TOGGLE).toHaveClass("show");
    expect(DROPDOWN_TOGGLE).toHaveClass("dropup");

    // close
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

    await click(getPickerCell("15")); // select some day
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
                            class="{ selected: state.checked }"
                            checked="state.checked"
                            closingMode="'none'"
                            onSelected.bind="onSelected">
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

    // This test checks that if a dropdown element opens a dialog with a dropdown inside,
    // opening this dropdown will not close the first dropdown.
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
                            <button class="parent-item" t-on-click="clicked">Click me</button>
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
    await click(".outside-dialog");
    await animationFrame();
    expect(".modal-dialog").toHaveCount(1);
    expect(DROPDOWN_MENU).toHaveCount(1);

    await click(".modal-dialog .btn-primary");
    await animationFrame();
    expect(".modal-dialog").toHaveCount(0);
    expect(DROPDOWN_MENU).toHaveCount(1);
    await click(".outside-parent");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
});

test("t-if t-else as toggler", async () => {
    let state = undefined;

    class Parent extends Component {
        static components = { Dropdown };
        static props = [];
        static template = xml`
                <Dropdown>
                    <button t-if="state.foo === 'bar'">Coucou</button>
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

    // Open
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Close
    await click(DROPDOWN_TOGGLE);
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    // Change button then open
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

    // Open dialog
    await click(".root-dropdown");
    await animationFrame();
    await click(".root-button");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Open dropdown in dialog => both dropdown should be open
    await click(".dialog-dropdown");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    // Click inside dropdown inside dialog => both dropdown should not close
    await click(".dialog-button");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    // Click outside dropdown inside dialog => only first dropdown should be open
    await click(".inside-dialog");
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
    // Dropdown needs one tick to open as it goes through the popover/overlay service
    await animationFrame(); // Wait for first dropdown to open
    await animationFrame(); // Wait for second dropdown
    await animationFrame(); // Wait for third dropdown
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
    await click("div.outside");
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

    // Open the 2-level dropdowns
    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();

    // Select item (closingMode=none)
    await click(".item1");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    // Select item (closingMode=closest)
    await click(".item2");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1);

    // Reopen second level dropdown
    await click(".dropdown-b");
    await animationFrame();

    // Select item (closingMode=all)
    await click(".item3");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);

    // Reopen the 2-level dropdowns
    await click(".dropdown-a");
    await animationFrame();
    await click(".dropdown-b");
    await animationFrame();

    // Select item (default should be closingMode=all)
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
            ["recursive.Template"]: /* xml */ `
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

    // Each sub-dropdown needs a tick to open
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
                        <DropdownItem class="'first-first'" onSelected="() => onItemSelected('first-first')">O</DropdownItem>
                        <Dropdown>
                            <button class="second">Second</button>
                            <t t-set-slot="content">
                                <DropdownItem class="'second-first'" onSelected="() => onItemSelected('second-first')">O</DropdownItem>
                                <Dropdown>
                                    <button class="third">Third</button>
                                    <t t-set-slot="content">
                                        <DropdownItem class="'third-first'" onSelected="() => onItemSelected('third-first')">O</DropdownItem>
                                        <DropdownItem class="'third-last'" onSelected="() => onItemSelected('third-last')">O</DropdownItem>
                                    </t>
                                </Dropdown>
                                <DropdownItem class="'second-last'" onSelected="() => onItemSelected('second-last')">O</DropdownItem>
                            </t>
                        </Dropdown>
                        <DropdownItem class="'first-last'" onSelected="() => onItemSelected('first-last')">O</DropdownItem>
                    </t>
                </Dropdown>
            `;
    }
    await mountWithCleanup(Parent);
    expect(DROPDOWN_MENU).toHaveCount(0, {
        message: "menus are closed at the start",
    });

    // Highlighting and selecting items
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
                        : lastActiveElement
                ).toBeFocused();
            } else {
                // no active element means that the main dropdown is closed
                expect(document.activeElement).toHaveClass("first");
            }
        }
        if (step.selected !== undefined) {
            const verify = step.selected === false ? [] : [step.selected];
            // step ${stepIndex}: selected item is correct
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

    // Highlighting and selecting items
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
                                <DropdownItem t-if="state.foo" class="three">three</DropdownItem>
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

    // Open the menu
    await click(".one");
    await animationFrame();
    expect.verifySteps(["submenu mounted"]);

    // Open the submenu
    await click(".two");
    await animationFrame();
    // Change submenu content
    parentState.foo = true;
    await animationFrame();
    expect.verifySteps(["submenu patched"]);

    // Change submenu content
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

    // Open main dropdown
    await click(".main");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1, {
        message: "1st menu is opened",
    });

    // Mouse enter sub dropdown
    await hover(".sub");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);

    // Mouse enter the adjacent dropdown item
    await hover(".item");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(1, {
        message: "only 1st menu is opened",
    });
});

test.tags("desktop");
test("multi-level dropdown: unsubscribe all keynav when root close", async () => {
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

    const env = await makeMockEnv();
    patchWithCleanup(env.services.hotkey, {
        add(key) {
            const remove = super.add(...arguments);
            registeredHotkeys.add(key);
            return () => {
                remove();
                removedHotkeys.add(key);
            };
        },
    });

    await mountWithCleanup(Parent, { env });
    expect(DROPDOWN_MENU).toHaveCount(0);
    expect(registeredHotkeys.size).toBe(0);

    // Open dropdowns one by one
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
    checkKeys(registeredHotkeys);

    // Close third
    await press("escape");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(2);
    checkKeys(removedHotkeys);

    // Reset hover
    await hover(getFixture());

    // Reopen second
    await hover(".third");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(3);
    checkKeys(registeredHotkeys);

    // Close third, second and first
    await press("escape");
    await animationFrame();
    checkKeys(removedHotkeys);

    await press("escape");
    await animationFrame();
    checkKeys(removedHotkeys);

    await press("escape");
    await animationFrame();
    expect(DROPDOWN_MENU).toHaveCount(0);
    checkKeys(removedHotkeys);
});
