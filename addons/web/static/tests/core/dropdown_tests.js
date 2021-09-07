/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { makeTestEnv } from "../helpers/mock_env";
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../helpers/utils";
import { registerCleanup } from "../helpers/cleanup";

const { mount } = owl;
const serviceRegistry = registry.category("services");
const mainComponentsRegistry = registry.category("main_components");

let env;
let parent;
let target;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        target = getFixture();
        registerCleanup(() => parent.destroy());
    });

    QUnit.module("Dropdown");

    QUnit.test("can be rendered", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`<Dropdown/>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(
            parent.el.outerHTML,
            '<div class="o_dropdown"><button class="o_dropdown_toggler "><span></span></button></div>'
        );
        assert.containsOnce(parent.el, "button.o_dropdown_toggler");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
    });

    QUnit.test("can be rendered (custom tag)", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`<Dropdown tag="'ged'"/>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(
            parent.el.outerHTML,
            '<ged class="o_dropdown"><button class="o_dropdown_toggler "><span></span></button></ged>'
        );
        assert.containsOnce(parent.el, "button.o_dropdown_toggler");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
    });

    QUnit.test("DropdownItem can be rendered", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`<DropdownItem>coucou</DropdownItem>`;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.strictEqual(parent.el.outerHTML, '<li class="o_dropdown_item">coucou</li>');
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
        await click(parent.el, "button.o_dropdown_toggler");
        assert.hasClass(parent.el, "o_dropdown one");
        const toggler = parent.el.querySelector("button");
        assert.hasClass(toggler, "o_dropdown_toggler two");
        const menu = parent.el.querySelector("ul");
        assert.hasClass(menu, "o_dropdown_menu three");
        const item = parent.el.querySelector("li");
        assert.hasClass(item, "o_dropdown_item four");
    });

    QUnit.test("menu can be toggled", async (assert) => {
        assert.expect(5);
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
        await click(parent.el, "button.o_dropdown_toggler");
        assert.verifySteps(["beforeOpen"]);
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
        beforeOpenProm.resolve();
        await nextTick();
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
        await click(parent.el, "button.o_dropdown_toggler");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
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
        await click(parent.el, "button.o_dropdown_toggler");
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
        await click(parent.el, "div.outside");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
        await click(parent.el, "button.o_dropdown_toggler");
        await click(parent.el, "ul.o_dropdown_menu li");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
        await click(parent.el, "button.o_dropdown_toggler");
        await click(parent.el, "ul.o_dropdown_menu li");
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
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
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
        assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
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
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
        await click(parent.el, "div.outside");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        await click(parent.el, ".o_dropdown_item:not(.o_dropdown)");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        // Select item (parentClosingMode=none)
        await click(parent.el, "li.item1");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        // Select item (parentClosingMode=closest)
        await click(parent.el, "li.item2");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 1);
        // Reopen second level dropdown
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        // Select item (parentClosingMode=all)
        await click(parent.el, "li.item3");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
        // Reopen the 2-level dropdowns
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        // Select item (default should be parentClosingMode=all)
        await click(parent.el, "li.item4");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        // As two listeners are defined in the template,
        // clicking once the item would execute the handler twice.
        await click(parent.el, ".o_dropdown_item:not(.o_dropdown)");
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
            [...parent.el.querySelectorAll("button,.o_dropdown_item:not(.o_dropdown)")].map(
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
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            assert.containsOnce(one, "ul.o_dropdown_menu");
            // Hover on TWO
            const two = parent.el.querySelector(".two");
            two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            assert.verifySteps(["beforeOpen"]);
            await nextTick();
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            assert.containsNone(two, "ul.o_dropdown_menu");
            beforeOpenProm.resolve();
            await nextTick();
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            assert.containsOnce(two, "ul.o_dropdown_menu");
            // Hover on THREE
            const three = parent.el.querySelector(".three");
            three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            assert.containsOnce(three, "ul.o_dropdown_menu");
            // Click on OUTSIDE
            await click(parent.el, "div.outside");
            assert.containsNone(parent.el, "ul.o_dropdown_menu");
            // Hover on ONE, TWO, THREE
            one.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            two.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            three.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsNone(parent.el, "ul.o_dropdown_menu");
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
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            // Hover on BAR1
            const bar1 = parent.el.querySelector(".bar1");
            bar1.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            assert.containsNone(bar1, "ul.o_dropdown_menu");
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
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            // Click on FOO
            await click(parent.el, ".foo button");
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            // Hover on BAR1
            const bar1 = parent.el.querySelector(".bar1");
            bar1.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
            await nextTick();
            assert.containsOnce(parent.el, "ul.o_dropdown_menu");
            assert.containsNone(bar1, "ul.o_dropdown_menu");
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
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
        // Click on two
        await click(parent.el, ".two button");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        // Click on one again
        await click(parent.el, ".one button");
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
        assert.containsNone(parent.el.querySelector(".one"), "ul.o_dropdown_menu");
        // Hover on one
        const one = parent.el.querySelector(".one");
        one.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
        assert.containsNone(parent.el.querySelector(".one"), "ul.o_dropdown_menu");
        // Click outside
        await click(parent.el, "div.outside");
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
    });

    QUnit.test("dropdowns keynav", async (assert) => {
        assert.expect(26);
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
        assert.containsNone(parent.el, ".o_dropdown_menu", "menu is closed at start");

        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            parent.el,
            ".o_dropdown_menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Navigate with arrows
        assert.containsNone(
            parent.el,
            ".o_dropdown_menu > .focus",
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
            assert.hasClass(parent.el.querySelector(".o_dropdown_menu > .focus"), step.expected);
        }

        // Select last one activated in previous scenario (item1)
        triggerHotkey("enter");
        await nextTick();
        assert.containsNone(parent.el, ".o_dropdown_menu", "menu is closed after item selection");

        // Reopen dropdown
        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            parent.el,
            ".o_dropdown_menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Select second item through data-hotkey attribute
        triggerHotkey("2", true);
        await nextTick();
        assert.containsNone(parent.el, ".o_dropdown_menu", "menu is closed after item selection");

        // Reopen dropdown
        triggerHotkey("m", true);
        await nextTick();
        assert.containsOnce(
            parent.el,
            ".o_dropdown_menu",
            "menu is opened after pressing the toggler hotkey"
        );

        // Close dropdown with keynav
        triggerHotkey("escape");
        await nextTick();
        assert.containsNone(parent.el, ".o_dropdown_menu", "menu is closed after item selection");

        assert.verifySteps(["1", "2"], "items should have been selected in this order");
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
        assert.containsOnce(parent, ".o_dropdown");
        assert.containsNone(parent, ".o_dropdown .o_dropdown_menu");
        assert.containsNone(parent, ".o_dropdown button.o_dropdown_toggler");
        await click(parent.el, ".my_custom_toggler");
        assert.containsOnce(parent, ".o_dropdown .o_dropdown_menu");
        assert.containsN(parent, ".o_dropdown .o_dropdown_menu .o_dropdown_item", 2);
    });

    QUnit.test("multi-level dropdown: keynav", async (assert) => {
        assert.expect(126);
        class Parent extends owl.Component {
            onItemSelected(ev) {
                const { payload } = ev.detail;
                assert.step(payload.val);
            }
        }
        Parent.template = owl.tags.xml`
            <Dropdown class="first" hotkey="'1'" t-on-dropdown-item-selected="onItemSelected">
                <DropdownItem class="first-first" payload="{val:'first-first'}" hotkey="'a'">O</DropdownItem>
                <Dropdown tag="'li'" class="second" hotkey="'2'">
                    <DropdownItem class="second-first" payload="{val:'second-first'}" hotkey="'b'">O</DropdownItem>
                    <Dropdown tag="'li'" class="third" hotkey="'3'">
                        <DropdownItem class="third-first" payload="{val:'third-first'}" hotkey="'c'">O</DropdownItem>
                        <DropdownItem class="third-last" payload="{val:'third-last'}" hotkey="'d'">O</DropdownItem>
                    </Dropdown>
                    <DropdownItem class="second-last" payload="{val:'second-last'}" hotkey="'e'">O</DropdownItem>
                </Dropdown>
                <DropdownItem class="first-last" payload="{val:'first-last'}" hotkey="'f'">O</DropdownItem>
            </Dropdown>
        `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsNone(parent.el, ".o_dropdown_menu", "menus are closed at start");

        // Open through hotkeys
        triggerHotkey("alt+2");
        await nextTick();
        assert.containsNone(parent.el, ".o_dropdown_menu", "no menu is opened");

        triggerHotkey("alt+1");
        await nextTick();
        assert.containsOnce(parent.el, ".o_dropdown_menu", "first menu is opened");

        triggerHotkey("alt+2");
        await nextTick();
        assert.containsN(parent.el, ".o_dropdown_menu", 2, "second menu is opened");

        triggerHotkey("alt+3");
        await nextTick();
        assert.containsN(parent.el, ".o_dropdown_menu", 3, "both menus are opened");

        // Close through hotkeys
        triggerHotkey("escape");
        await nextTick();
        assert.containsN(parent.el, ".o_dropdown_menu", 2, "third menu is closed");

        triggerHotkey("escape");
        await nextTick();
        assert.containsOnce(parent.el, ".o_dropdown_menu", "second menu is closed");

        triggerHotkey("escape");
        await nextTick();
        assert.containsNone(parent.el, ".o_dropdown_menu", "both menus are closed");

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
            { hotkey: "alt+e", selected: false },
            { hotkey: "alt+f", selected: "first-last" },
            { hotkey: "alt+1" },
            { hotkey: "alt+2", highlighted: ["second", "second-first"] },
            { hotkey: "alt+3", highlighted: ["second", "third", "third-first"] },
            { hotkey: "alt+d", selected: "third-last" },
            { hotkey: "alt+1" },
            { hotkey: "alt+2", highlighted: ["second", "second-first"] },
            { hotkey: "alt+e", selected: "second-last" },
        ];

        for (const [stepIndex, step] of scenarioSteps.entries()) {
            triggerHotkey(step.hotkey);
            await nextTick();
            if (step.highlighted !== undefined) {
                let index = 0;
                const activeElements = parent.el.querySelectorAll(".focus");
                assert.ok(
                    activeElements.length === step.highlighted.length,
                    `step ${stepIndex}: all active elements to check are found`
                );
                for (const element of activeElements) {
                    assert.hasClass(element, step.highlighted[index++]);
                }
            }
            if (step.selected !== undefined) {
                const verify = step.selected === false ? [] : [step.selected];
                assert.verifySteps(verify, `step ${stepIndex}: selected item is correct`);
            }
        }
    });

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
        assert.containsNone(parent.el, ".o_dropdown_menu", "menus are closed at start");
        assert.strictEqual(hotkeyRegistrationsCount, 0, "no hotkey registered");

        // Open dropdowns one by one
        await click(parent.el, ".first");
        assert.containsOnce(parent.el, ".o_dropdown_menu", "1st menu is opened");
        assert.strictEqual(hotkeyRegistrationsCount, 10, "1st menu hotkeys registered");

        await click(parent.el, ".second");
        assert.containsN(parent.el, ".o_dropdown_menu", 2, "2nd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 20, "2nd menu hotkeys also registered");

        await click(parent.el, ".third");
        assert.containsN(parent.el, ".o_dropdown_menu", 3, "3rd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 30, "3rd menu hotkeys also registered");

        // Close second
        await click(parent.el, ".second");
        assert.containsN(parent.el, ".o_dropdown_menu", 1, "only 1st menu stay opened");
        assert.strictEqual(hotkeyRegistrationsCount, 10, "only 1st menu hotkeys registered");

        // Reopen second
        await click(parent.el, ".second");
        assert.containsN(parent.el, ".o_dropdown_menu", 2, "2nd menu is also opened");
        assert.strictEqual(hotkeyRegistrationsCount, 20, "2nd menu hotkeys also registered");

        // Close first
        await click(parent.el, ".first");
        assert.containsNone(parent.el, ".o_dropdown_menu", "all menus are now closed");
        assert.strictEqual(hotkeyRegistrationsCount, 0, "no hotkey registration left");
    });
});
