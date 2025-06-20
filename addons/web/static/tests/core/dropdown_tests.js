/** @odoo-module **/

import { App, Component, onMounted, onPatched, useRef, useState, xml } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { registerCleanup } from "../helpers/cleanup";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import {
    click,
    getFixture,
    makeDeferred,
    mockTimeout,
    mount,
    mouseEnter,
    mouseLeave,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerHotkey,
} from "../helpers/utils";
import { makeParent } from "./tooltip/tooltip_service_tests";
import { getPickerCell } from "./datetime/datetime_test_helpers";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
import { Dialog } from "@web/core/dialog/dialog";
import { dialogService } from "@web/core/dialog/dialog_service";

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

    QUnit.module("Dropdown");

    QUnit.test("can be rendered", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`<Dropdown/>`;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.querySelector(".dropdown").outerHTML,
            '<div class="o-dropdown dropdown o-dropdown--no-caret"><button type="button" class="dropdown-toggle" tabindex="0" aria-expanded="false"></button></div>'
        );
        assert.containsOnce(target, "button.dropdown-toggle");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("DropdownItem can be rendered as <span/>", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`<DropdownItem>coucou</DropdownItem>`;
        Parent.components = { DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.querySelector(".dropdown-item").outerHTML,
            '<span class="dropdown-item" role="menuitem" tabindex="0">coucou</span>'
        );
    });

    QUnit.test("DropdownItem (with href prop) can be rendered as <a/>", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`<DropdownItem href="'#'">coucou</DropdownItem>`;
        Parent.components = { DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.querySelector(".dropdown-item").outerHTML,
            '<a class="dropdown-item" role="menuitem" tabindex="0" href="#">coucou</a>'
        );
    });

    QUnit.test("DropdownItem: prevents click default with href", async (assert) => {
        assert.expect(4);
        // A DropdownItem should preventDefault a click as it may take the shape
        // of an <a/> tag with an [href] attribute and e.g. could change the url when clicked.
        patchWithCleanup(DropdownItem.prototype, {
            onClick(ev) {
                assert.ok(!ev.defaultPrevented);
                super.onClick(...arguments);
                const href = ev.target.getAttribute("href");
                // defaultPrevented only if props.href is defined
                assert.ok(href !== null ? ev.defaultPrevented : !ev.defaultPrevented);
            },
        });
        class Parent extends Component {}
        Parent.template = xml`
            <Dropdown>
                <DropdownItem class="'link'" href="'#'"/>
                <DropdownItem class="'nolink'" />
            </Dropdown>`;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        // The item containing the link class contains an href prop,
        // which will turn it into <a href=> So it must be defaultPrevented
        // The other one not contain any href props, it must not be defaultPrevented,
        // so as not to prevent the background change flow for example
        await click(target, "button.dropdown-toggle");
        await click(target, ".link");
        await click(target, "button.dropdown-toggle");
        await click(target, ".nolink");
    });

    QUnit.test("can be styled", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <Dropdown class="'one'" togglerClass="'two'" menuClass="'three'">
            <DropdownItem class="'four'" />
        </Dropdown>`;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle");
        assert.hasClass(target.querySelector(".o-dropdown"), "dropdown one");
        const toggler = target.querySelector(".dropdown-toggle");
        assert.hasClass(toggler, "two");
        const menu = target.querySelector(".dropdown-menu");
        assert.hasClass(menu, "three");
        const item = target.querySelector(".dropdown-item");
        assert.hasClass(item, "four");
    });

    QUnit.test("menu can be toggled", async (assert) => {
        const beforeOpenProm = makeDeferred();
        class Parent extends Component {
            constructor() {
                super(...arguments);
                this.beforeOpen = () => {
                    assert.step("beforeOpen");
                    return beforeOpenProm;
                };
            }
        }
        Parent.template = xml`<Dropdown beforeOpen="beforeOpen"/>`;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle");
        assert.verifySteps(["beforeOpen"]);
        assert.containsNone(target, ".dropdown-menu");
        assert.strictEqual(target.querySelector("button.dropdown-toggle").ariaExpanded, "false");
        beforeOpenProm.resolve();
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        assert.strictEqual(target.querySelector(".dropdown-menu").getAttribute("role"), "menu");
        assert.strictEqual(target.querySelector("button.dropdown-toggle").ariaExpanded, "true");
        await click(target, "button.dropdown-toggle");
        assert.containsNone(target, ".dropdown-menu");
        assert.strictEqual(target.querySelector("button.dropdown-toggle").ariaExpanded, "false");
    });

    QUnit.test("initial open state can be true", async (assert) => {
        assert.expect(3);
        class Parent extends Component {
            constructor() {
                super(...arguments);
                this.beforeOpen = () => {
                    assert.step("beforeOpen");
                };
            }
        }
        Parent.template = xml`<Dropdown startOpen="true" beforeOpen="beforeOpen"/>`;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.verifySteps(["beforeOpen"]);
        assert.containsOnce(target, ".dropdown-menu");
    });

    QUnit.test("close on outside click", async (assert) => {
        patchWithCleanup(Dropdown.prototype, {
            close() {
                assert.step("dropdown will close");
                super.close();
            },
        });
        class Parent extends Component {
            clicked() {
                assert.verifySteps(
                    ["dropdown will close"],
                    "the dropdown already knows it should close"
                );
            }
        }
        Parent.template = xml`
        <div>
          <div class="outside" t-on-click.stop="clicked">outside</div>
          <Dropdown/>
        </div>
      `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");
        await click(target, "div.outside");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("close on item selection", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <Dropdown>
            <DropdownItem/>
        </Dropdown>
      `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle");
        await click(target, ".dropdown-menu .dropdown-item");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("hold position on hover", async (assert) => {
        let parentState;
        class Parent extends Component {
            setup() {
                this.state = useState({ filler: false });
                parentState = this.state;
            }
            static template = xml`
                <div t-if="state.filler" class="filler" style="height: 100px;"/>
                <Dropdown holdOnHover="true">
                </Dropdown>
            `;
            static components = { Dropdown };
        }
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsNone(target, ".dropdown-menu");
        await click(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");
        const menuBox1 = target.querySelector(".dropdown-menu").getBoundingClientRect();

        // Pointer enter the dropdown menu
        await mouseEnter(target, ".dropdown-menu");

        // Add a filler to the parent
        assert.containsNone(target, ".filler");
        parentState.filler = true;
        await nextTick();
        assert.containsOnce(target, ".filler");
        const menuBox2 = target.querySelector(".dropdown-menu").getBoundingClientRect();
        assert.strictEqual(menuBox2.top - menuBox1.top, 0);

        // Pointer leave the dropdown menu
        await mouseLeave(target, ".dropdown-menu");
        const menuBox3 = target.querySelector(".dropdown-menu").getBoundingClientRect();
        assert.strictEqual(menuBox3.top - menuBox1.top, 100);
    });

    QUnit.test("unlock position after close", async (assert) => {
        class Parent extends Component {
            static template = xml`
                <div style="margin-left: 200px;">
                    <Dropdown holdOnHover="true" position="'bottom-end'">
                    </Dropdown>
                </div>
            `;
            static components = { Dropdown };
        }
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsNone(target, ".dropdown-menu");
        await click(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");
        const menuBox1 = target.querySelector(".dropdown-menu").getBoundingClientRect();

        // Pointer enter the dropdown menu to lock the menu
        await mouseEnter(target, ".dropdown-menu");
        // close the menu
        await click(target);
        assert.containsNone(target, ".dropdown-menu");

        // and reopen it
        await click(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");
        const menuBox2 = target.querySelector(".dropdown-menu").getBoundingClientRect();
        assert.strictEqual(menuBox2.left - menuBox1.left, 0);
    });

    QUnit.test("payload received on item selection", async (assert) => {
        class Parent extends Component {
            onItemSelected(value) {
                assert.equal(value, 42);
            }
        }
        Parent.template = xml`
        <Dropdown>
            <DropdownItem onSelected="() => onItemSelected(42)"/>
        </Dropdown>
      `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle");
        await click(target, ".dropdown-menu .dropdown-item");
    });

    QUnit.test("multi-level dropdown: can be rendered and toggled", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <Dropdown>
            <Dropdown>
                <Dropdown/>
            </Dropdown>
        </Dropdown>
      `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        assert.containsN(target, ".dropdown-menu", 3);
    });

    QUnit.test("multi-level dropdown: initial open state can be true", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <Dropdown startOpen="true">
            <Dropdown startOpen="true">
                <Dropdown startOpen="true"/>
            </Dropdown>
        </Dropdown>
      `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsN(target, ".dropdown-menu", 3);
    });

    QUnit.test("multi-level dropdown: close on outside click", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <div>
          <div class="outside">outside</div>
          <Dropdown>
              <Dropdown>
                  <Dropdown/>
              </Dropdown>
          </Dropdown>
        </div>
      `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        assert.containsN(target, ".dropdown-menu", 3);
        await click(target, "div.outside");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown: close on item selection", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <Dropdown>
            <Dropdown>
                <DropdownItem/>
            </Dropdown>
        </Dropdown>
      `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        assert.containsN(target, ".dropdown-menu", 2);
        assert.containsN(target, ".dropdown-item", 2);
        assert.containsOnce(target, ".dropdown-menu > .dropdown > .dropdown-toggle.dropdown-item");
        assert.containsOnce(target, ".dropdown-menu > .dropdown-item");
        await click(target, ".dropdown-menu > .dropdown-item");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown: parent closing modes on item selection", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <Dropdown>
            <Dropdown>
                <DropdownItem class="'item1'" parentClosingMode="'none'" />
                <DropdownItem class="'item2'" parentClosingMode="'closest'" />
                <DropdownItem class="'item3'" parentClosingMode="'all'" />
                <DropdownItem class="'item4'" />
            </Dropdown>
        </Dropdown>
      `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        // Open the 2-level dropdowns
        await click(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        assert.containsN(target, ".dropdown-menu", 2);
        // Select item (parentClosingMode=none)
        await click(target, ".item1");
        assert.containsN(target, ".dropdown-menu", 2);
        // Select item (parentClosingMode=closest)
        await click(target, ".item2");
        assert.containsN(target, ".dropdown-menu", 1);
        // Reopen second level dropdown
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        assert.containsN(target, ".dropdown-menu", 2);
        // Select item (parentClosingMode=all)
        await click(target, ".item3");
        assert.containsNone(target, ".dropdown-menu");
        // Reopen the 2-level dropdowns
        await click(target, "button.dropdown-toggle:last-child");
        await mouseEnter(target, "button.dropdown-toggle:last-child");
        assert.containsN(target, ".dropdown-menu", 2);
        // Select item (default should be parentClosingMode=all)
        await click(target, ".item4");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown: recursive template can be rendered", async (assert) => {
        class Parent extends Component {
            setup() {
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
        Parent.template = "recursive.Template";
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        const app = new App(Parent, {
            env,
            templates,
            test: true,
        });
        registerCleanup(() => app.destroy());
        app.addTemplate(
            "recursive.Template",
            `<Dropdown startOpen="true">
                <t t-set-slot="toggler">
                    <t t-esc="name" />
                </t>
                <t t-foreach="items" t-as="item" t-key="item_index">

                <t t-if="!item.children.length">
                    <DropdownItem><t t-esc="item.name"/></DropdownItem>
                </t>

                <t t-else="" t-call="recursive.Template">
                    <t t-set="name" t-value="item.name" />
                    <t t-set="items" t-value="item.children" />
                </t>

                </t>
            </Dropdown>`
        );
        await app.mount(target);
        assert.deepEqual(
            [...target.querySelectorAll("button,.dropdown-menu > .dropdown-item")].map(
                (el) => el.textContent
            ),
            [
                "foo",
                "foo-0",
                "foo-00",
                "foo-01",
                "foo-010",
                "foo-011",
                "foo-012",
                "foo-0120",
                "foo-0121",
                "foo-0122",
                "foo-02",
                "foo-1",
                "foo-2",
            ]
        );
    });

    QUnit.test(
        "siblings dropdowns: when one is open, others can be toggled on mouse-enter",
        async (assert) => {
            assert.expect(13);
            const beforeOpenProm = makeDeferred();
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.beforeOpen = () => {
                        assert.step("beforeOpen");
                        return beforeOpenProm;
                    };
                }
            }
            Parent.template = xml`
        <div>
          <Dropdown class="'one'" />
          <Dropdown class="'two'" beforeOpen="beforeOpen"/>
          <Dropdown class="'three'" />
          <div class="outside">OUTSIDE</div>
        </div>
      `;
            Parent.components = { Dropdown };
            env = await makeTestEnv();
            await mount(Parent, target, { env });
            // Click on ONE
            const one = target.querySelector(".one");
            await click(one, "button");
            assert.verifySteps([]);
            assert.containsOnce(target, ".dropdown-menu");
            assert.containsOnce(one, ".dropdown-menu");
            // Hover on TWO
            const two = target.querySelector(".two");
            two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            assert.verifySteps(["beforeOpen"]);
            await nextTick();
            assert.containsOnce(target, ".dropdown-menu");
            assert.containsNone(two, ".dropdown-menu");
            beforeOpenProm.resolve();
            await nextTick();
            assert.containsOnce(target, ".dropdown-menu");
            assert.containsOnce(two, ".dropdown-menu");
            // Hover on THREE
            const three = target.querySelector(".three");
            three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(target, ".dropdown-menu");
            assert.containsOnce(three, ".dropdown-menu");
            // Click on OUTSIDE
            await click(target, "div.outside");
            assert.containsNone(target, ".dropdown-menu");
            // Hover on ONE, TWO, THREE
            one.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsNone(target, ".dropdown-menu");
        }
    );

    QUnit.test(
        "siblings dropdowns: when non-sibling is open, other must not be toggled on mouse-enter",
        async (assert) => {
            class Parent extends Component {}
            Parent.template = xml`
        <div>
          <div><Dropdown class="'foo'" /></div>
          <Dropdown class="'bar1'" />
          <Dropdown class="'bar2'" />
        </div>
      `;
            Parent.components = { Dropdown };
            env = await makeTestEnv();
            await mount(Parent, target, { env });
            // Click on FOO
            await click(target, ".foo button");
            assert.containsOnce(target, ".dropdown-menu");
            // Hover on BAR1
            const bar1 = target.querySelector(".bar1");
            bar1.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(target, ".dropdown-menu");
            assert.containsNone(bar1, ".dropdown-menu");
        }
    );

    QUnit.test(
        "siblings dropdowns: when one is open, then non-sibling toggled, siblings must not be toggled on mouse-enter",
        async (assert) => {
            class Parent extends Component {}
            Parent.template = xml`
        <div>
          <div><Dropdown class="'foo'" /></div>
          <Dropdown class="'bar1'" />
          <Dropdown class="'bar2'" />
        </div>
      `;
            Parent.components = { Dropdown };
            env = await makeTestEnv();
            await mount(Parent, target, { env });
            // Click on BAR1
            await click(target, ".bar1 button");
            assert.containsOnce(target, ".dropdown-menu");
            // Click on FOO
            await click(target, ".foo button");
            assert.containsOnce(target, ".dropdown-menu");
            // Hover on BAR1
            const bar1 = target.querySelector(".bar1");
            bar1.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(target, ".dropdown-menu");
            assert.containsNone(bar1, ".dropdown-menu");
        }
    );

    QUnit.test("siblings dropdowns with autoOpen", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <div>
          <Dropdown class="'one'" autoOpen="false"/>
          <Dropdown class="'two'" autoOpen="false"/>
          <Dropdown class="'three'"/>
          <Dropdown class="'four'"/>
          <div class="outside">OUTSIDE</div>
        </div>
      `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        // Click on one
        await click(target, ".one button");
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsOnce(target, ".one .dropdown-menu");
        // Hover on two
        const two = target.querySelector(".two");
        two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsOnce(target, ".one .dropdown-menu");
        // Hover on three
        const three = target.querySelector(".three");
        three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsOnce(target, ".one .dropdown-menu");
        // Click outside
        await click(target, "div.outside");
        assert.containsNone(target, ".dropdown-menu");
        // Click on three
        await click(target, ".three button");
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsOnce(target, ".three .dropdown-menu");
        // Hover on two
        two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsOnce(target, ".three .dropdown-menu");
        // Hover on four
        const four = target.querySelector(".four");
        four.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsOnce(target, ".four .dropdown-menu");
    });

    QUnit.test("siblings dropdowns: toggler focused on mouseenter", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
        <div>
            <Dropdown class="'one'" />
            <Dropdown class="'two'" />
        </div>
        `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        // Click on one
        target.querySelector(".one button").focus(); // mocks a real click flow
        await click(target, ".one button");
        assert.strictEqual(document.activeElement, target.querySelector(".one button"));
        assert.containsOnce(target, ".dropdown-menu");
        // Hover on two
        const two = target.querySelector(".two");
        two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.strictEqual(document.activeElement, two.querySelector("button"));
    });

    QUnit.test("dropdowns keynav", async (assert) => {
        assert.expect(41);
        class Parent extends Component {
            onItemSelected(value) {
                assert.step(value.toString());
            }
        }
        Parent.template = xml`
        <Dropdown hotkey="'m'">
            <DropdownItem class="'item1'" onSelected="() => onItemSelected(1)">item1</DropdownItem>
            <DropdownItem class="'item2'" hotkey="'2'" onSelected="() => onItemSelected(2)">item2</DropdownItem>
            <DropdownItem class="'item3'" onSelected="() => onItemSelected(3)">item3</DropdownItem>
        </Dropdown>
      `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsNone(target, ".dropdown-menu", "menu is closed at start");

        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            target,
            ".dropdown-menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Navigate with arrows
        assert.containsNone(
            target,
            ".dropdown-menu > .focus",
            "menu should not have any active items"
        );

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

        for (const step of scenarioSteps) {
            triggerHotkey(step.hotkey);
            await nextTick();
            assert.hasClass(target.querySelector(".dropdown-menu > .focus"), step.expected);
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".dropdown-menu > .focus")
            );
        }

        // Select last one activated in previous scenario (item1)
        triggerHotkey("enter");
        await nextTick();
        assert.containsNone(target, ".dropdown-menu", "menu is closed after item selection");

        // Reopen dropdown
        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            target,
            ".dropdown-menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Select second item through data-hotkey attribute
        triggerHotkey("2", true);
        await nextTick();
        assert.containsNone(target, ".dropdown-menu", "menu is closed after item selection");

        // Reopen dropdown
        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            target,
            ".dropdown-menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Close dropdown with keynav
        triggerHotkey("escape");
        await nextTick();
        assert.containsNone(target, ".dropdown-menu", "menu is closed after item selection");

        assert.verifySteps(["1", "2"], "items should have been selected in this order");
    });

    QUnit.test("dropdowns keynav is not impacted by bootstrap", async (assert) => {
        class Parent extends Component {}
        Parent.components = { Dropdown };
        Parent.template = xml`
            <Dropdown startOpen="true">
                <select><option>foo</option></select>
            </Dropdown>
        `;
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".dropdown-menu", "menu is opened at start");
        const menu = target.querySelector(".dropdown-menu");

        // This class presence makes bootstrap ignore the below event
        assert.hasClass(menu, "o-dropdown--menu");

        const select = menu.querySelector("select");
        let ev = new KeyboardEvent("keydown", {
            bubbles: true,
            // Define the ArrowDown key with standard API (for hotkey_service)
            key: "ArrowDown",
            code: "ArrowDown",
        });
        select.dispatchEvent(ev);
        await nextTick();

        ev = new KeyboardEvent("keydown", {
            bubbles: true,
            // Define the ESC key with standard API (for hotkey_service)
            key: "Escape",
            code: "Escape",
        });
        select.dispatchEvent(ev);
        await nextTick();
        assert.containsNone(target, ".dropdown-menu", "menu is now closed");
    });

    QUnit.test("props toggler='parent'", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
            <div>
                <div class="my_custom_toggler">
                    Click Me
                    <Dropdown toggler="'parent'">
                        <DropdownItem>Element 1</DropdownItem>
                        <DropdownItem>Element 2</DropdownItem>
                    </Dropdown>
                </div>
            </div>`;

        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".dropdown");
        assert.containsNone(target, ".dropdown .dropdown-menu");
        assert.containsNone(target, ".dropdown button.dropdown-toggle");
        assert.strictEqual(target.querySelector(".my_custom_toggler").ariaExpanded, "false");
        await click(target, ".my_custom_toggler");
        assert.containsOnce(target, ".dropdown .dropdown-menu");
        assert.containsN(target, ".dropdown .dropdown-menu .dropdown-item", 2);
        assert.strictEqual(target.querySelector(".my_custom_toggler").ariaExpanded, "true");
    });

    QUnit.test("props toggler='parent': refocus toggler on close with keynav", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
            <div>
                <div class="my_custom_toggler">
                    Click Me
                    <Dropdown toggler="'parent'">
                        <DropdownItem>Element 1</DropdownItem>
                        <DropdownItem>Element 2</DropdownItem>
                    </Dropdown>
                </div>
            </div>`;
        Parent.components = { Dropdown, DropdownItem };

        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(document.activeElement, document.body);
        target.querySelector(".my_custom_toggler").focus(); // mocks a real click flow
        await click(target, ".my_custom_toggler");
        assert.strictEqual(document.activeElement, target.querySelector(".my_custom_toggler"));
        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".dropdown-item:first-child")
        );
        triggerHotkey("Escape");
        await nextTick();
        assert.strictEqual(document.activeElement, target.querySelector(".my_custom_toggler"));
    });

    QUnit.test("multi-level dropdown: keynav", async (assert) => {
        assert.expect(213);
        const { execRegisteredTimeouts } = mockTimeout();
        class Parent extends Component {
            onItemSelected(value) {
                assert.step(value);
            }
        }
        Parent.template = xml`
            <Dropdown class="'first'" hotkey="'1'">
                <DropdownItem class="'first-first'" onSelected="() => onItemSelected('first-first')">O</DropdownItem>
                <Dropdown class="'second'">
                    <DropdownItem class="'second-first'" onSelected="() => onItemSelected('second-first')">O</DropdownItem>
                    <Dropdown class="'third'">
                        <DropdownItem class="'third-first'" onSelected="() => onItemSelected('third-first')">O</DropdownItem>
                        <DropdownItem class="'third-last'" onSelected="() => onItemSelected('third-last')">O</DropdownItem>
                    </Dropdown>
                    <DropdownItem class="'second-last'" onSelected="() => onItemSelected('second-last')">O</DropdownItem>
                </Dropdown>
                <DropdownItem class="'first-last'" onSelected="() => onItemSelected('first-last')">O</DropdownItem>
            </Dropdown>
        `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsNone(target, ".dropdown-menu", "menus are closed at start");

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
            triggerHotkey(step.hotkey);
            execRegisteredTimeouts();
            await nextTick();
            if (step.highlighted !== undefined) {
                let index = 0;
                const activeElements = [...target.querySelectorAll(".focus")].map((el) =>
                    el.classList.contains("dropdown-toggle") ? el.parentElement : el
                );
                assert.ok(
                    activeElements.length === step.highlighted.length,
                    `step ${stepIndex}: all active elements to check are found`
                );
                for (const element of activeElements) {
                    assert.hasClass(element, step.highlighted[index++]);
                }
                const lastActiveElement = activeElements.slice(-1)[0];
                if (lastActiveElement) {
                    assert.hasClass(lastActiveElement, step.highlighted.slice(-1)[0]);
                    assert.strictEqual(
                        document.activeElement,
                        lastActiveElement.classList.contains("dropdown")
                            ? lastActiveElement.querySelector(":scope > .dropdown-toggle")
                            : lastActiveElement
                    );
                } else {
                    // no active element means that the main dropdown is closed
                    assert.hasClass(document.activeElement, "dropdown-toggle");
                    assert.hasClass(document.activeElement.parentElement, "first");
                }
            }
            if (step.selected !== undefined) {
                const verify = step.selected === false ? [] : [step.selected];
                assert.verifySteps(verify, `step ${stepIndex}: selected item is correct`);
            }
        }
    });

    QUnit.test("multi-level dropdown: keynav when rtl direction", async (assert) => {
        assert.expect(10);
        class Parent extends Component {}
        Parent.template = xml`
            <Dropdown class="'first'" hotkey="'1'">
                <DropdownItem class="'first-first'">O</DropdownItem>
                <Dropdown class="'second'">
                    <DropdownItem class="'second-first'">O</DropdownItem>
                </Dropdown>
            </Dropdown>
        `;
        Parent.components = { Dropdown, DropdownItem };
        serviceRegistry.add("localization", makeFakeLocalizationService({ direction: "rtl" }));
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsNone(target, ".dropdown-menu", "menus are closed at start");

        // Highlighting and selecting items
        const scenarioSteps = [
            { hotkey: "alt+1" },
            { hotkey: "arrowdown", highlighted: ["first-first"] },
            { hotkey: "arrowdown", highlighted: ["second"] },
            { hotkey: "arrowleft", highlighted: ["second", "second-first"] },
            { hotkey: "arrowright", highlighted: ["second"] },
        ];

        for (const [stepIndex, step] of scenarioSteps.entries()) {
            triggerHotkey(step.hotkey);
            await nextTick();
            if (step.highlighted !== undefined) {
                let index = 0;
                const activeElements = [...target.querySelectorAll(".focus")].map((el) =>
                    el.classList.contains("dropdown-toggle") ? el.parentElement : el
                );
                assert.ok(
                    activeElements.length === step.highlighted.length,
                    `step ${stepIndex}: all active elements to check are found`
                );
                for (const element of activeElements) {
                    assert.hasClass(element, step.highlighted[index++]);
                }
            }
        }
    });

    QUnit.test("multi-level dropdown: submenu keeps position when patched", async (assert) => {
        assert.expect(9);
        patchWithCleanup(Dropdown.prototype, {
            setup() {
                super.setup(...arguments);
                const isSubmenu = Boolean(this.parentDropdown);
                if (isSubmenu) {
                    onMounted(() => {
                        assert.step(`submenu mounted`);
                    });
                    const menuRef = useRef("menuRef");
                    let previousMenuRect;
                    onPatched(() => {
                        assert.step(`submenu patched`);
                        if (this.state.open) {
                            const subMenuRect = menuRef.el.getBoundingClientRect();
                            if (previousMenuRect) {
                                assert.strictEqual(subMenuRect.top, previousMenuRect.top);
                                assert.strictEqual(subMenuRect.left, previousMenuRect.left);
                            }
                            previousMenuRect = subMenuRect;
                        }
                    });
                }
            },
        });
        let parentState;
        class Parent extends Component {
            setup() {
                this.state = useState({ foo: false });
                parentState = this.state;
            }
        }
        Parent.template = /* xml */ xml`
            <Dropdown class="'outer'">
                <t t-set-slot="toggler">Outer</t>
                <Dropdown class="'inner'">
                    <t t-set-slot="toggler">Inner</t>
                    <DropdownItem t-if="state.foo">Inner</DropdownItem>
                </Dropdown>
            </Dropdown>
        `;
        Parent.components = { Dropdown, DropdownItem };

        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.verifySteps([]);

        // Open the menu
        await click(target, ".outer .dropdown-toggle");
        assert.verifySteps(["submenu mounted"]);

        // Open the submenu
        await triggerEvent(target, ".inner .dropdown-toggle", "mouseenter");
        assert.verifySteps(["submenu patched"]);

        // Change submenu content
        parentState.foo = true;
        await nextTick();
        assert.verifySteps(["submenu patched"]);
    });

    QUnit.test("showCaret props adds caret class", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
            <Dropdown class="'first'" hotkey="'1'" showCaret="true">
                <DropdownItem class="'first-first'">O</DropdownItem>
                <Dropdown class="'second'" showCaret="false">
                    <DropdownItem class="'second-first'">O</DropdownItem>
                </Dropdown>
            </Dropdown>
        `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsNone(
            target,
            ".first.o-dropdown--no-caret",
            "first dropdown should have a caret"
        );
        await click(target, ".dropdown-toggle");
        assert.containsOnce(
            target,
            ".second.o-dropdown--no-caret",
            "second dropdown should not have a caret"
        );
    });

    QUnit.test("caret should be repositioned to default direction when closed", async (assert) => {
        class Parent extends Component {
            static components = { Dropdown };
            static template = xml`
                <div style="height: 384px;"/> <!-- filler: takes half the runbot's browser_size -->
                <Dropdown showCaret="true">
                    <t t-set-slot="toggler">🍋</t>
                    <div style="height: 400px; width: 50px;"/> <!-- menu filler -->
                </Dropdown>
            `;
        }
        // The fixture should be shown for this test, as the positioning container is the html node
        target.style.position = "fixed";
        target.style.top = "0";
        target.style.left = "0";

        env = await makeTestEnv();
        await mount(Parent, target, { env });
        const dropdown = target.querySelector(".o-dropdown");
        assert.doesNotHaveClass(dropdown, "show");
        assert.hasClass(dropdown, "dropdown");

        // open
        await click(target, ".dropdown-toggle");
        await nextTick(); // awaits for the caret to get patched
        assert.hasClass(dropdown, "show");
        assert.hasClass(dropdown, "dropend");

        // close
        await click(target, ".dropdown-toggle");
        assert.doesNotHaveClass(dropdown, "show");
        assert.hasClass(dropdown, "dropdown");

        // open
        await click(target, ".dropdown-toggle");
        await nextTick(); // awaits for the caret to get patched
        assert.hasClass(dropdown, "show");
        assert.hasClass(dropdown, "dropend");
    });

    QUnit.test(
        "multi-level dropdown: mouseentering a dropdown item should close any subdropdown",
        async (assert) => {
            assert.expect(4);
            class Parent extends Component {}
            Parent.template = xml`
                <Dropdown togglerClass="'main'">
                    <Dropdown togglerClass="'sub'" />
                    <DropdownItem class="'item'" />
                </Dropdown>
            `;
            Parent.components = { Dropdown, DropdownItem };
            env = await makeTestEnv();
            await mount(Parent, target, { env });
            assert.containsNone(target, ".dropdown-menu", "menus are closed at start");

            // Open main dropdown
            await click(target, ".main");
            assert.containsOnce(target, ".dropdown-menu", "1st menu is opened");

            // Mouse enter sub dropdown
            await mouseEnter(target, ".sub");
            assert.containsN(target, ".dropdown-menu", 2, "all menus are opened");

            // Mouse enter the adjacent dropdown item
            await mouseEnter(target, ".item");
            assert.containsOnce(target, ".dropdown-menu", "only 1st menu is opened");
        }
    );

    QUnit.test("multi-level dropdown: unsubscribe all keynav when root close", async (assert) => {
        assert.expect(14);
        class Parent extends Component {}
        Parent.template = xml`
            <Dropdown togglerClass="'first'">
                <Dropdown togglerClass="'second'">
                    <Dropdown togglerClass="'third'"/>
                </Dropdown>
            </Dropdown>
        `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        let hotkeyRegistrationsCount = 0;
        patchWithCleanup(env.services.hotkey, {
            add() {
                const remove = super.add(...arguments);
                hotkeyRegistrationsCount += 1;
                return () => {
                    remove();
                    hotkeyRegistrationsCount -= 1;
                };
            },
        });
        await mount(Parent, target, { env });
        assert.containsNone(target, ".dropdown-menu", "menus are closed at start");
        assert.strictEqual(hotkeyRegistrationsCount, 0, "no hotkey registered");

        // Open dropdowns one by one
        await click(target, ".first");
        assert.containsOnce(target, ".dropdown-menu", "1st menu is opened");
        assert.strictEqual(hotkeyRegistrationsCount, 10, "1st menu hotkeys registered");

        await mouseEnter(target, ".second");
        assert.containsN(target, ".dropdown-menu", 2, "2nd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 20, "2nd menu hotkeys also registered");

        await mouseEnter(target, ".third");
        assert.containsN(target, ".dropdown-menu", 3, "3rd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 30, "3rd menu hotkeys also registered");

        // Close third
        triggerHotkey("escape");
        await nextTick();
        assert.containsN(target, ".dropdown-menu", 2, "two menus still opened");
        assert.strictEqual(hotkeyRegistrationsCount, 20, "two menus hotkeys registered");

        // Reopen second
        await mouseEnter(target, ".third");
        assert.containsN(target, ".dropdown-menu", 3, "3rd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 30, "3rd menu hotkeys also registered");

        // Close third, second and first
        triggerHotkey("escape");
        await nextTick();
        triggerHotkey("escape");
        await nextTick();
        triggerHotkey("escape");
        await nextTick();
        assert.containsNone(target, ".dropdown-menu", "all menus are now closed");
        assert.strictEqual(hotkeyRegistrationsCount, 0, "no hotkey registration left");
    });

    QUnit.test("Dropdown with a tooltip", async (assert) => {
        assert.expect(1);

        class Parent extends Component {}
        Parent.template = xml`<Dropdown tooltip="'My tooltip'"></Dropdown>`;
        Parent.components = { Dropdown };

        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.querySelector("button.dropdown-toggle").dataset.tooltip,
            "My tooltip"
        );
    });

    QUnit.test("Dropdown with a tooltip", async (assert) => {
        assert.expect(2);

        class MyComponent extends Component {}
        MyComponent.template = xml`
            <Dropdown tooltip="'My tooltip'">
                <DropdownItem/>
            </Dropdown>`;
        MyComponent.components = { Dropdown };

        await makeParent(MyComponent);
        await mouseEnter(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".o-tooltip");
        assert.strictEqual(target.querySelector(".o-tooltip").textContent, "My tooltip");
    });

    QUnit.test(
        "Dropdown with a date picker inside do not close when a click occurs in date picker",
        async (assert) => {
            registry.category("services").add("datetime_picker", datetimePickerService);
            class MyComponent extends Component {}
            MyComponent.template = xml`
                <Dropdown>
                    <t t-set-slot="toggler">
                        Dropdown toggler
                    </t>
                    <DateTimeInput />
                </Dropdown>
            `;
            MyComponent.components = { DateTimeInput, Dropdown };

            await makeParent(MyComponent);

            assert.containsNone(target, ".o-dropdown--menu");

            await click(target, ".dropdown-toggle");

            assert.containsOnce(target, ".o-dropdown--menu");
            assert.containsNone(target, ".o_datetime_picker");
            assert.strictEqual(target.querySelector(".o_datetime_input").value, "");

            await click(target, ".o_datetime_input");

            assert.containsOnce(target, ".o-dropdown--menu");
            assert.containsOnce(target, ".o_datetime_picker");
            assert.strictEqual(target.querySelector(".o_datetime_input").value, "");

            await click(getPickerCell("15")); // select some day

            assert.containsOnce(target, ".o-dropdown--menu");
            assert.containsOnce(target, ".o_datetime_picker");
            assert.notOk(target.querySelector(".o_datetime_input").value === "");
        }
    );

    QUnit.test("onOpened callback props called after the menu has been mounted", async (assert) => {
        const beforeOpenProm = makeDeferred();
        class Parent extends Component {
            beforeOpenCallback() {
                assert.step("beforeOpened");
                return beforeOpenProm;
            }
            onOpenedCallback() {
                assert.step("onOpened");
            }
        }
        Parent.template = xml`
            <Dropdown onOpened.bind="onOpenedCallback" beforeOpen.bind="beforeOpenCallback" />
        `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle");
        assert.verifySteps(["beforeOpened"]);
        beforeOpenProm.resolve();
        await nextTick();
        assert.verifySteps(["onOpened"]);
    });

    QUnit.test("dropdown button can be disabled", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`<Dropdown disabled="true"/>`;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.querySelector(".dropdown").outerHTML,
            '<div class="o-dropdown dropdown o-dropdown--no-caret"><button type="button" class="dropdown-toggle" disabled="" tabindex="0" aria-expanded="false"></button></div>'
        );
    });

    QUnit.test("Dropdown with CheckboxItem: toggle value", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({ checked: false });
            }
            onSelected() {
                this.state.checked = !this.state.checked;
            }
        }
        Parent.template = xml`
            <Dropdown>
                <t t-set-slot="toggler">Click to open</t>
                <CheckboxItem
                    class="{ selected: state.checked }"
                    checked="state.checked"
                    parentClosingMode="'none'"
                    onSelected.bind="onSelected">
                    My checkbox item
                </CheckboxItem>
            </Dropdown>`;
        Parent.components = { Dropdown, CheckboxItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, ".dropdown-toggle");
        assert.strictEqual(
            target.querySelector(".dropdown-item").outerHTML,
            `<span class="dropdown-item" role="menuitemcheckbox" tabindex="0" aria-checked="false"> My checkbox item </span>`
        );
        await click(target, ".dropdown-item");
        assert.strictEqual(
            target.querySelector(".dropdown-item").outerHTML,
            `<span class="dropdown-item selected" role="menuitemcheckbox" tabindex="0" aria-checked="true"> My checkbox item </span>`
        );
    });

    QUnit.test("don't close dropdown outside the active element", async (assert) => {
        // This test checks that if a dropdown element opens a dialog with a dropdown inside,
        // opening this dropdown will not close the first dropdown.
        class CustomDialog extends Component {}
        CustomDialog.template = xml`
            <Dialog title="'Welcome'">
                <Dropdown>
                    <DropdownItem>Item</DropdownItem>
                </Dropdown>
                <div class="outside_dialog">Outside Dialog</div>
            </Dialog>`;
        CustomDialog.components = { Dialog, Dropdown, DropdownItem };

        const mainComponentRegistry = registry.category("main_components");
        clearRegistryWithCleanup(mainComponentRegistry);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("l10n", makeFakeLocalizationService());

        class PseudoWebClient extends Component {
            setup() {
                this.Components = mainComponentRegistry.getEntries();
            }
            clicked() {
                env.services.dialog.add(CustomDialog);
            }
        }
        PseudoWebClient.template = xml`
                <div>
                    <div>
                        <t t-foreach="Components" t-as="C" t-key="C[0]">
                            <t t-component="C[1].Component" t-props="C[1].props"/>
                        </t>
                    </div>
                    <div>
                        <Dropdown>
                            <button class="click-me" t-on-click="clicked">Click me</button>
                        </Dropdown>
                        <div class="outside_parent">Outside Parent</div>
                    </div>
                </div>
            `;
        PseudoWebClient.components = { Dropdown };

        env = await makeTestEnv();
        await mount(PseudoWebClient, target, { env });
        await click(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");
        await click(target, "button.click-me");
        assert.containsOnce(target, ".modal-dialog");
        await click(target, ".modal-dialog button.dropdown-toggle");
        assert.containsN(target, ".dropdown-menu", 2);
        await click(target, ".outside_dialog");
        assert.containsOnce(target, ".modal-dialog");
        assert.containsN(target, ".dropdown-menu", 1);
        await click(target, ".modal-dialog .btn-primary");
        assert.containsNone(target, ".modal-dialog");
        assert.containsN(target, ".dropdown-menu", 1);
        await click(target, ".outside_parent");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown is well positioned", async (assert) => {
        class Parent extends Component {}
        Parent.template = xml`
           <Dropdown class="'parent'" menuClass="'border-0'">
                <DropdownItem>A</DropdownItem>
                <Dropdown class="'first'" menuClass="'border-0'">
                    <t t-set-slot="toggler">
                        B
                    </t>
                    <DropdownItem>B A</DropdownItem>
                    <DropdownItem>B C</DropdownItem>
                </Dropdown>
                <Dropdown class="'second'" menuClass="'border-0'">
                    <t t-set-slot="toggler">
                        C
                    </t>
                    <DropdownItem>C A</DropdownItem>
                    <DropdownItem>C B</DropdownItem>
                </Dropdown>
            </Dropdown>
        `;
        Parent.components = { Dropdown, DropdownItem };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        await click(target, "button.dropdown-toggle:last-child");
        const parentMenu = target.querySelector(".parent .dropdown-menu");
        const parentMenuBox = parentMenu.getBoundingClientRect();

        // Hover first sub-dropdown
        await mouseEnter(target, ".o-dropdown.first > button");
        await nextTick();
        let currentDropdown = target.querySelector(".first .dropdown-menu");
        let currentDropdownBox = currentDropdown.getBoundingClientRect();
        //Check X position of the first subdropdown, should not overlap parent dropdown
        assert.ok(currentDropdownBox.x >= parentMenuBox.x + parentMenuBox.width);
        //Check Y position of the first subdropdown, should not overlap parent dropdown
        let parentTogglerBox = parentMenu.querySelector(".show").getBoundingClientRect();
        let currentTogglerBox = currentDropdown.querySelector(".focus").getBoundingClientRect();
        assert.ok(Math.abs(parentTogglerBox.y - currentTogglerBox.y) < 5);

        // Hover second sub-dropdown
        await mouseEnter(target, ".o-dropdown.second > button");
        await nextTick();
        currentDropdown = target.querySelector(".second .dropdown-menu");
        currentDropdownBox = currentDropdown.getBoundingClientRect();
        //Check X position of the second subdropdown, should not overlap parent dropdown
        assert.ok(currentDropdownBox.x >= parentMenuBox.x + parentMenuBox.width);
        //Check Y position of the first subdropdown, should not overlap parent dropdown
        parentTogglerBox = parentMenu.querySelector(".show").getBoundingClientRect();
        currentTogglerBox = currentDropdown.querySelector(".focus").getBoundingClientRect();
        assert.ok(Math.abs(parentTogglerBox.y - currentTogglerBox.y) < 5);
    });
});
