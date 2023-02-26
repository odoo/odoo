/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { DropdownItem } from "../../src/core/dropdown/dropdown_item";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import {
    click,
    getFixture,
    makeDeferred,
    mouseEnter,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerHotkey,
} from "../helpers/utils";

const { mount } = owl;
const serviceRegistry = registry.category("services");

let env;
let parent;
let target;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        target = getFixture();
        registerCleanup(() => parent.destroy());
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("Dropdown");

    QUnit.test("can be rendered", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`<Dropdown/>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(
            parent.el.outerHTML,
            '<div class="o-dropdown dropdown o-dropdown--no-caret"><button class="dropdown-toggle  " aria-expanded="false"></button></div>'
        );
        assert.containsOnce(parent.el, "button.dropdown-toggle");
        assert.containsNone(parent.el, ".dropdown-menu");
    });

    QUnit.test("DropdownItem can be rendered as <span/>", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`<DropdownItem>coucou</DropdownItem>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(
            parent.el.outerHTML,
            '<span role="menuitem" tabindex="0" class="dropdown-item">coucou</span>'
        );
    });

    QUnit.test("DropdownItem (with href prop) can be rendered as <a/>", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`<DropdownItem href="'#'">coucou</DropdownItem>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(
            parent.el.outerHTML,
            '<a href="#" role="menuitem" tabindex="0" class="dropdown-item">coucou</a>'
        );
    });

    QUnit.test("DropdownItem: prevents click default with href", async (assert) => {
        assert.expect(4);
        // A DropdownItem should preventDefault a click as it may take the shape
        // of an <a/> tag with an [href] attribute and e.g. could change the url when clicked.
        patchWithCleanup(DropdownItem.prototype, {
            onClick(ev) {
                assert.ok(!ev.defaultPrevented);
                this._super(...arguments);
                const href = ev.target.getAttribute("href");
                // defaultPrevented only if props.href is defined
                assert.ok(href !== null ? ev.defaultPrevented : !ev.defaultPrevented);
            },
        });
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
            <Dropdown>
                <DropdownItem class="link" href="'#'"/>
                <DropdownItem class="nolink" />
            </Dropdown>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        // The item containing the link class contains an href prop,
        // which will turn it into <a href=> So it must be defaultPrevented
        // The other one not contain any href props, it must not be defaultPrevented,
        // so as not to prevent the background change flow for example
        await click(parent.el, "button.dropdown-toggle");
        await click(parent.el, ".link");
        await click(parent.el, "button.dropdown-toggle");
        await click(parent.el, ".nolink");
    });

    QUnit.test("can be styled", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown class="one" togglerClass="'two'" menuClass="'three'">
            <DropdownItem class="four" />
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle");
        assert.hasClass(parent.el, "dropdown one");
        const toggler = parent.el.querySelector(".dropdown-toggle");
        assert.hasClass(toggler, "two");
        const menu = parent.el.querySelector(".dropdown-menu");
        assert.hasClass(menu, "three");
        const item = parent.el.querySelector(".dropdown-item");
        assert.hasClass(item, "four");
    });

    QUnit.test("menu can be toggled", async (assert) => {
        const beforeOpenProm = makeDeferred();
        class Parent extends owl.Component {
            constructor() {
                super(...arguments);
                this.beforeOpen = () => {
                    assert.step("beforeOpen");
                    return beforeOpenProm;
                };
            }
        }
        Parent.template = owl.tags.xml`<Dropdown beforeOpen="beforeOpen"/>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle");
        assert.verifySteps(["beforeOpen"]);
        assert.containsNone(parent.el, ".dropdown-menu");
        assert.strictEqual(parent.el.querySelector("button.dropdown-toggle").ariaExpanded, "false");
        beforeOpenProm.resolve();
        await nextTick();
        assert.containsOnce(parent.el, ".dropdown-menu");
        assert.strictEqual(parent.el.querySelector(".dropdown-menu").getAttribute("role"), "menu");
        assert.strictEqual(parent.el.querySelector("button.dropdown-toggle").ariaExpanded, "true");
        await click(parent.el, "button.dropdown-toggle");
        assert.containsNone(parent.el, ".dropdown-menu");
        assert.strictEqual(parent.el.querySelector("button.dropdown-toggle").ariaExpanded, "false");
    });

    QUnit.test("initial open state can be true", async (assert) => {
        assert.expect(3);
        class Parent extends owl.Component {
            constructor() {
                super(...arguments);
                this.beforeOpen = () => {
                    assert.step("beforeOpen");
                };
            }
        }
        Parent.template = owl.tags.xml`<Dropdown startOpen="true" beforeOpen="beforeOpen"/>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.verifySteps(["beforeOpen"]);
        assert.containsOnce(parent.el, ".dropdown-menu");
    });

    QUnit.test("close on outside click", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <div>
          <div class="outside">outside</div>
          <Dropdown/>
        </div>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle");
        assert.containsOnce(parent.el, ".dropdown-menu");
        await click(parent.el, "div.outside");
        assert.containsNone(parent.el, ".dropdown-menu");
    });

    QUnit.test("close on item selection", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
            <DropdownItem/>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle");
        await click(parent.el, ".dropdown-menu .dropdown-item");
        assert.containsNone(parent.el, ".dropdown-menu");
    });

    QUnit.test("payload received on item selection", async (assert) => {
        class Parent extends owl.Component {
            onItemSelected(ev) {
                assert.deepEqual(ev.detail.payload, { answer: 42 });
            }
        }
        Parent.template = owl.tags.xml`
        <Dropdown t-on-dropdown-item-selected="onItemSelected">
            <DropdownItem payload="{ answer: 42 }"/>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle");
        await click(parent.el, ".dropdown-menu .dropdown-item");
    });

    QUnit.test("multi-level dropdown: can be rendered and toggled", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
            <Dropdown>
                <Dropdown/>
            </Dropdown>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        assert.containsN(parent.el, ".dropdown-menu", 3);
    });

    QUnit.test("multi-level dropdown: initial open state can be true", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown startOpen="true">
            <Dropdown startOpen="true">
                <Dropdown startOpen="true"/>
            </Dropdown>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsN(parent.el, ".dropdown-menu", 3);
    });

    QUnit.test("multi-level dropdown: close on outside click", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <div>
          <div class="outside">outside</div>
          <Dropdown>
              <Dropdown>
                  <Dropdown/>
              </Dropdown>
          </Dropdown>
        </div>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        assert.containsN(parent.el, ".dropdown-menu", 3);
        await click(parent.el, "div.outside");
        assert.containsNone(parent.el, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown: close on item selection", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
            <Dropdown>
                <DropdownItem/>
            </Dropdown>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        assert.containsN(parent.el, ".dropdown-menu", 2);
        assert.containsN(parent.el, ".dropdown-item", 2);
        assert.containsOnce(
            parent.el,
            ".dropdown-menu > .dropdown > .dropdown-toggle.dropdown-item"
        );
        assert.containsOnce(parent.el, ".dropdown-menu > .dropdown-item");
        await click(parent.el, ".dropdown-menu > .dropdown-item");
        assert.containsNone(parent.el, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown: parent closing modes on item selection", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
            <Dropdown>
                <DropdownItem class="item1" parentClosingMode="'none'" />
                <DropdownItem class="item2" parentClosingMode="'closest'" />
                <DropdownItem class="item3" parentClosingMode="'all'" />
                <DropdownItem class="item4" />
            </Dropdown>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        // Open the 2-level dropdowns
        await click(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        assert.containsN(parent.el, ".dropdown-menu", 2);
        // Select item (parentClosingMode=none)
        await click(parent.el, ".item1");
        assert.containsN(parent.el, ".dropdown-menu", 2);
        // Select item (parentClosingMode=closest)
        await click(parent.el, ".item2");
        assert.containsN(parent.el, ".dropdown-menu", 1);
        // Reopen second level dropdown
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        assert.containsN(parent.el, ".dropdown-menu", 2);
        // Select item (parentClosingMode=all)
        await click(parent.el, ".item3");
        assert.containsNone(parent.el, ".dropdown-menu");
        // Reopen the 2-level dropdowns
        await click(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        assert.containsN(parent.el, ".dropdown-menu", 2);
        // Select item (default should be parentClosingMode=all)
        await click(parent.el, ".item4");
        assert.containsNone(parent.el, ".dropdown-menu");
    });

    QUnit.test("multi-level dropdown: payload bubbles on item selection", async (assert) => {
        assert.expect(2);
        class Parent extends owl.Component {
            onItemSelected(ev) {
                assert.deepEqual(ev.detail.payload, { answer: 42 });
            }
        }
        Parent.template = owl.tags.xml`
        <Dropdown t-on-dropdown-item-selected="onItemSelected">
            <Dropdown t-on-dropdown-item-selected="onItemSelected">
                <DropdownItem payload="{ answer: 42 }" />
            </Dropdown>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.dropdown-toggle:last-child");
        await mouseEnter(parent.el, "button.dropdown-toggle:last-child");
        // As two listeners are defined in the template,
        // clicking once the item would execute the handler twice.
        await click(parent.el, ".dropdown-menu > .dropdown-item");
    });

    QUnit.test("multi-level dropdown: recursive template can be rendered", async (assert) => {
        const recursiveTemplate = `
        <Dropdown startOpen="true">
            <t t-set-slot="toggler">
                <t t-esc="name" />
            </t>
            <t t-foreach="items" t-as="item">

              <t t-if="!item.children.length">
                <DropdownItem t-esc="item.name" />
              </t>

              <t t-else="" t-call="recursive.Template">
                <t t-set="name" t-value="item.name" />
                <t t-set="items" t-value="item.children" />
              </t>

            </t>
        </Dropdown>
    `;
        class Parent extends owl.Component {
            constructor() {
                super(...arguments);
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
        env = await makeTestEnv();
        env.qweb.addTemplate("recursive.Template", recursiveTemplate);
        parent = await mount(Parent, { env, target });
        assert.deepEqual(
            [...parent.el.querySelectorAll("button,.dropdown-menu > .dropdown-item")].map(
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
            class Parent extends owl.Component {
                constructor() {
                    super(...arguments);
                    this.beforeOpen = () => {
                        assert.step("beforeOpen");
                        return beforeOpenProm;
                    };
                }
            }
            Parent.template = owl.tags.xml`
        <div>
          <Dropdown class="one" />
          <Dropdown class="two" beforeOpen="beforeOpen"/>
          <Dropdown class="three" />
          <div class="outside">OUTSIDE</div>
        </div>
      `;
            env = await makeTestEnv();
            parent = await mount(Parent, { env, target });
            // Click on ONE
            const one = parent.el.querySelector(".one");
            await click(one, "button");
            assert.verifySteps([]);
            assert.containsOnce(parent.el, ".dropdown-menu");
            assert.containsOnce(one, ".dropdown-menu");
            // Hover on TWO
            const two = parent.el.querySelector(".two");
            two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            assert.verifySteps(["beforeOpen"]);
            await nextTick();
            assert.containsOnce(parent.el, ".dropdown-menu");
            assert.containsNone(two, ".dropdown-menu");
            beforeOpenProm.resolve();
            await nextTick();
            assert.containsOnce(parent.el, ".dropdown-menu");
            assert.containsOnce(two, ".dropdown-menu");
            // Hover on THREE
            const three = parent.el.querySelector(".three");
            three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(parent.el, ".dropdown-menu");
            assert.containsOnce(three, ".dropdown-menu");
            // Click on OUTSIDE
            await click(parent.el, "div.outside");
            assert.containsNone(parent.el, ".dropdown-menu");
            // Hover on ONE, TWO, THREE
            one.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsNone(parent.el, ".dropdown-menu");
        }
    );

    QUnit.test(
        "siblings dropdowns: when non-sibling is open, other must not be toggled on mouse-enter",
        async (assert) => {
            class Parent extends owl.Component {}
            Parent.template = owl.tags.xml`
        <div>
          <div><Dropdown class="foo" /></div>
          <Dropdown class="bar1" />
          <Dropdown class="bar2" />
        </div>
      `;
            env = await makeTestEnv();
            parent = await mount(Parent, { env, target });
            // Click on FOO
            await click(parent.el, ".foo button");
            assert.containsOnce(parent.el, ".dropdown-menu");
            // Hover on BAR1
            const bar1 = parent.el.querySelector(".bar1");
            bar1.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(parent.el, ".dropdown-menu");
            assert.containsNone(bar1, ".dropdown-menu");
        }
    );

    QUnit.test(
        "siblings dropdowns: when one is open, then non-sibling toggled, siblings must not be toggled on mouse-enter",
        async (assert) => {
            class Parent extends owl.Component {}
            Parent.template = owl.tags.xml`
        <div>
          <div><Dropdown class="foo" /></div>
          <Dropdown class="bar1" />
          <Dropdown class="bar2" />
        </div>
      `;
            env = await makeTestEnv();
            parent = await mount(Parent, { env, target });
            // Click on BAR1
            await click(parent.el, ".bar1 button");
            assert.containsOnce(parent.el, ".dropdown-menu");
            // Click on FOO
            await click(parent.el, ".foo button");
            assert.containsOnce(parent.el, ".dropdown-menu");
            // Hover on BAR1
            const bar1 = parent.el.querySelector(".bar1");
            bar1.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(parent.el, ".dropdown-menu");
            assert.containsNone(bar1, ".dropdown-menu");
        }
    );

    QUnit.test("siblings dropdowns with manualOnly props", async (assert) => {
        assert.expect(7);
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <div>
          <Dropdown class="one" manualOnly="true"/>
          <Dropdown class="two" manualOnly="true"/>
          <div class="outside">OUTSIDE</div>
        </div>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        // Click on one
        await click(parent.el, ".one button");
        assert.containsOnce(parent.el, ".dropdown-menu");
        // Click on two
        await click(parent.el, ".two button");
        assert.containsN(parent.el, ".dropdown-menu", 2);
        // Click on one again
        await click(parent.el, ".one button");
        assert.containsOnce(parent.el, ".dropdown-menu");
        assert.containsNone(parent.el.querySelector(".one"), ".dropdown-menu");
        // Hover on one
        const one = parent.el.querySelector(".one");
        one.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(parent.el, ".dropdown-menu");
        assert.containsNone(parent.el.querySelector(".one"), ".dropdown-menu");
        // Click outside
        await click(parent.el, "div.outside");
        assert.containsOnce(parent.el, ".dropdown-menu");
    });

    QUnit.test("siblings dropdowns: toggler focused on mouseenter", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <div>
            <Dropdown class="one" />
            <Dropdown class="two" />
        </div>
        `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        // Click on one
        parent.el.querySelector(".one button").focus(); // mocks a real click flow
        await click(parent.el, ".one button");
        assert.strictEqual(document.activeElement, parent.el.querySelector(".one button"));
        assert.containsOnce(parent.el, ".dropdown-menu");
        // Hover on two
        const two = parent.el.querySelector(".two");
        two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.strictEqual(document.activeElement, two.querySelector("button"));
    });

    QUnit.test("dropdowns keynav", async (assert) => {
        assert.expect(41);
        class Parent extends owl.Component {
            onItemSelected(ev) {
                const { payload } = ev.detail;
                assert.step(payload.val.toString());
            }
        }
        Parent.template = owl.tags.xml`
        <Dropdown hotkey="'m'" t-on-dropdown-item-selected="onItemSelected">
            <DropdownItem class="item1" payload="{val:1}">item1</DropdownItem>
            <DropdownItem class="item2" hotkey="'2'" payload="{val:2}">item2</DropdownItem>
            <DropdownItem class="item3" payload="{val:3}">item3</DropdownItem>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsNone(parent.el, ".dropdown-menu", "menu is closed at start");

        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            parent.el,
            ".dropdown-menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Navigate with arrows
        assert.containsNone(
            parent.el,
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
            assert.hasClass(parent.el.querySelector(".dropdown-menu > .focus"), step.expected);
            assert.strictEqual(
                document.activeElement,
                parent.el.querySelector(".dropdown-menu > .focus")
            );
        }

        // Select last one activated in previous scenario (item1)
        triggerHotkey("enter");
        await nextTick();
        assert.containsNone(parent.el, ".dropdown-menu", "menu is closed after item selection");

        // Reopen dropdown
        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            parent.el,
            ".dropdown-menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Select second item through data-hotkey attribute
        triggerHotkey("2", true);
        await nextTick();
        assert.containsNone(parent.el, ".dropdown-menu", "menu is closed after item selection");

        // Reopen dropdown
        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            parent.el,
            ".dropdown-menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Close dropdown with keynav
        triggerHotkey("escape");
        await nextTick();
        assert.containsNone(parent.el, ".dropdown-menu", "menu is closed after item selection");

        assert.verifySteps(["1", "2"], "items should have been selected in this order");
    });

    QUnit.test("dropdowns keynav is not impacted by bootstrap", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
            <Dropdown startOpen="true">
                <select><option>foo</option></select>
            </Dropdown>
        `;
        env = await makeTestEnv();
        await mount(Parent, { env, target });
        assert.containsOnce(target, ".dropdown-menu", "menu is opened at start");
        const menu = target.querySelector(".dropdown-menu");

        // This class presence makes bootstrap ignore the below event
        assert.hasClass(menu, "o-dropdown--menu");

        const select = menu.querySelector("select");
        const ev = new KeyboardEvent("keydown", {
            bubbles: true,
            // Define the ESC key with standard API (for hotkey_service)
            key: "Escape",
            code: "Escape",
            // Define the ESC key with deprecated API (for bootstrap)
            keyCode: 27,
            which: 27,
        });
        select.dispatchEvent(ev);
        await nextTick();
        assert.containsNone(target, ".dropdown-menu", "menu is now closed");
    });

    QUnit.test("props toggler='parent'", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
            <div>
                <div class="my_custom_toggler">
                    Click Me
                    <Dropdown toggler="'parent'">
                        <DropdownItem>Element 1</DropdownItem>
                        <DropdownItem>Element 2</DropdownItem>
                    </Dropdown>
                </div>
            </div>`;

        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsOnce(parent, ".dropdown");
        assert.containsNone(parent, ".dropdown .dropdown-menu");
        assert.containsNone(parent, ".dropdown button.dropdown-toggle");
        assert.strictEqual(parent.el.querySelector(".my_custom_toggler").ariaExpanded, "false");
        await click(parent.el, ".my_custom_toggler");
        assert.containsOnce(parent, ".dropdown .dropdown-menu");
        assert.containsN(parent, ".dropdown .dropdown-menu .dropdown-item", 2);
        assert.strictEqual(parent.el.querySelector(".my_custom_toggler").ariaExpanded, "true");
    });

    QUnit.test("props toggler='parent': refocus toggler on close with keynav", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
            <div>
                <div class="my_custom_toggler">
                    Click Me
                    <Dropdown toggler="'parent'">
                        <DropdownItem>Element 1</DropdownItem>
                        <DropdownItem>Element 2</DropdownItem>
                    </Dropdown>
                </div>
            </div>`;

        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(document.activeElement, document.body);
        parent.el.querySelector(".my_custom_toggler").focus(); // mocks a real click flow
        await click(parent.el, ".my_custom_toggler");
        assert.strictEqual(document.activeElement, parent.el.querySelector(".my_custom_toggler"));
        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            parent.el.querySelector(".dropdown-item:first-child")
        );
        triggerHotkey("Escape");
        await nextTick();
        assert.strictEqual(document.activeElement, parent.el.querySelector(".my_custom_toggler"));
    });

    QUnit.test("multi-level dropdown: keynav", async (assert) => {
        assert.expect(213);
        class Parent extends owl.Component {
            onItemSelected(ev) {
                const { payload } = ev.detail;
                assert.step(payload.val);
            }
        }
        Parent.template = owl.tags.xml`
            <Dropdown class="first" hotkey="'1'" t-on-dropdown-item-selected="onItemSelected">
                <DropdownItem class="first-first" payload="{val:'first-first'}">O</DropdownItem>
                <Dropdown class="second">
                    <DropdownItem class="second-first" payload="{val:'second-first'}">O</DropdownItem>
                    <Dropdown class="third">
                        <DropdownItem class="third-first" payload="{val:'third-first'}">O</DropdownItem>
                        <DropdownItem class="third-last" payload="{val:'third-last'}">O</DropdownItem>
                    </Dropdown>
                    <DropdownItem class="second-last" payload="{val:'second-last'}">O</DropdownItem>
                </Dropdown>
                <DropdownItem class="first-last" payload="{val:'first-last'}">O</DropdownItem>
            </Dropdown>
        `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsNone(parent.el, ".dropdown-menu", "menus are closed at start");

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
            await nextTick();
            if (step.highlighted !== undefined) {
                let index = 0;
                const activeElements = [...parent.el.querySelectorAll(".focus")].map((el) =>
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
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
            <Dropdown class="first" hotkey="'1'">
                <DropdownItem class="first-first">O</DropdownItem>
                <Dropdown class="second">
                    <DropdownItem class="second-first">O</DropdownItem>
                </Dropdown>
            </Dropdown>
        `;
        serviceRegistry.add("localization", makeFakeLocalizationService({ direction: "rtl" }));
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsNone(parent.el, ".dropdown-menu", "menus are closed at start");

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
                const activeElements = [...parent.el.querySelectorAll(".focus")].map((el) =>
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

    QUnit.test(
        "multi-level dropdown: mouseentering a dropdown item should close any subdropdown",
        async (assert) => {
            assert.expect(4);
            class Parent extends owl.Component {}
            Parent.template = owl.tags.xml`
                <Dropdown togglerClass="'main'">
                    <Dropdown togglerClass="'sub'" />
                    <DropdownItem class="item" />
                </Dropdown>
            `;
            env = await makeTestEnv();
            parent = await mount(Parent, { env, target });
            assert.containsNone(parent.el, ".dropdown-menu", "menus are closed at start");

            // Open main dropdown
            await click(parent.el, ".main");
            assert.containsOnce(parent.el, ".dropdown-menu", "1st menu is opened");

            // Mouse enter sub dropdown
            await mouseEnter(parent.el, ".sub");
            assert.containsN(parent.el, ".dropdown-menu", 2, "all menus are opened");

            // Mouse enter the adjacent dropdown item
            await mouseEnter(parent.el, ".item");
            assert.containsOnce(parent.el, ".dropdown-menu", "only 1st menu is opened");
        }
    );

    QUnit.test("multi-level dropdown: unsubscribe all keynav when root close", async (assert) => {
        assert.expect(14);
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
            <Dropdown togglerClass="'first'">
                <Dropdown togglerClass="'second'">
                    <Dropdown togglerClass="'third'"/>
                </Dropdown>
            </Dropdown>
        `;
        env = await makeTestEnv();
        let hotkeyRegistrationsCount = 0;
        patchWithCleanup(env.services.hotkey, {
            add() {
                const remove = this._super(...arguments);
                hotkeyRegistrationsCount += 1;
                return () => {
                    remove();
                    hotkeyRegistrationsCount -= 1;
                };
            },
        });
        parent = await mount(Parent, { env, target });
        assert.containsNone(parent.el, ".dropdown-menu", "menus are closed at start");
        assert.strictEqual(hotkeyRegistrationsCount, 0, "no hotkey registered");

        // Open dropdowns one by one
        await click(parent.el, ".first");
        assert.containsOnce(parent.el, ".dropdown-menu", "1st menu is opened");
        assert.strictEqual(hotkeyRegistrationsCount, 10, "1st menu hotkeys registered");

        await mouseEnter(parent.el, ".second");
        assert.containsN(parent.el, ".dropdown-menu", 2, "2nd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 20, "2nd menu hotkeys also registered");

        await mouseEnter(parent.el, ".third");
        assert.containsN(parent.el, ".dropdown-menu", 3, "3rd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 30, "3rd menu hotkeys also registered");

        // Close third
        triggerHotkey("escape");
        await nextTick();
        assert.containsN(parent.el, ".dropdown-menu", 2, "two menus still opened");
        assert.strictEqual(hotkeyRegistrationsCount, 20, "two menus hotkeys registered");

        // Reopen second
        await mouseEnter(parent.el, ".third");
        assert.containsN(parent.el, ".dropdown-menu", 3, "3rd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 30, "3rd menu hotkeys also registered");

        // Close third, second and first
        triggerHotkey("escape");
        await nextTick();
        triggerHotkey("escape");
        await nextTick();
        triggerHotkey("escape");
        await nextTick();
        assert.containsNone(parent.el, ".dropdown-menu", "all menus are now closed");
        assert.strictEqual(hotkeyRegistrationsCount, 0, "no hotkey registration left");
    });
});
