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

const { mount } = owl;
const serviceRegistry = registry.category("services");
const mainComponentsRegistry = registry.category("main_components");

let env;
let parent;
let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        target = getFixture();
    });
    hooks.afterEach(() => {
        parent.destroy();
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
          <t t-set-slot="menu">
            <DropdownItem class="four" />
          </t>
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

    QUnit.test("close on activeElement change", async (assert) => {
        class Parent extends owl.Component {
            setup() {
                this.dc = mainComponentsRegistry.get("DialogContainer");
            }
        }
        Parent.template = owl.tags.xml`
            <div>
                <Dropdown />
                <t t-component="dc.Component" t-props="dc.props" />
            </div>
        `;
        class CustomDialog extends Dialog {}
        CustomDialog.title = "Dropdown Killer";
        serviceRegistry.add("dialog", dialogService);
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.o_dropdown_toggler");
        await nextTick(); // await that the dropdown sets its active element
        assert.containsOnce(parent.el, "ul.o_dropdown_menu");
        env.services.dialog.add(CustomDialog);
        await nextTick(); // await that the dropdown starts to close
        await nextTick(); // await that the dropdown is closed
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
    });

    QUnit.test("close on item selection", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
          <t t-set-slot="menu">
            <DropdownItem/>
          </t>
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
          <t t-set-slot="menu">
            <DropdownItem payload="{ answer: 42 }"/>
          </t>
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
          <t t-set-slot="menu">
            <Dropdown>
              <t t-set-slot="menu">
                <Dropdown/>
              </t>
            </Dropdown>
          </t>
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
          <t t-set-slot="menu">
            <Dropdown startOpen="true">
              <t t-set-slot="menu">
                <Dropdown startOpen="true"/>
              </t>
            </Dropdown>
          </t>
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
            <t t-set-slot="menu">
              <Dropdown>
                <t t-set-slot="menu">
                  <Dropdown/>
                </t>
              </Dropdown>
            </t>
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

    QUnit.test("multi-level dropdown: close on activeElement change", async (assert) => {
        patchWithCleanup(Dropdown.prototype, {
            close() {
                assert.step("closed");
                this._super();
            },
        });
        class Parent extends owl.Component {
            setup() {
                this.dc = mainComponentsRegistry.get("DialogContainer");
            }
        }
        Parent.template = owl.tags.xml`
            <div>
                <Dropdown>
                    <t t-set-slot="menu">
                        <Dropdown>
                            <t t-set-slot="menu">
                                <Dropdown/>
                            </t>
                        </Dropdown>
                    </t>
                </Dropdown>
                <t t-component="dc.Component" t-props="dc.props" />
            </div>
        `;
        class CustomDialog extends Dialog {}
        CustomDialog.title = "Dropdown Killer";
        serviceRegistry.add("dialog", dialogService);
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
        await nextTick(); // await that the dropdowns set their active elements
        env.services.dialog.add(CustomDialog);
        assert.verifySteps([]);
        await nextTick(); // await that the dropdowns start to close
        await nextTick(); // await that the dropdowns are closed
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
        assert.verifySteps(["closed", "closed", "closed"]);
    });

    QUnit.test("multi-level dropdown: close on item selection", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
          <t t-set-slot="menu">
            <Dropdown>
              <t t-set-slot="menu">
                <DropdownItem/>
              </t>
            </Dropdown>
          </t>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
        await click(parent.el, "li");
        assert.containsNone(parent.el, "ul.o_dropdown_menu");
    });

    QUnit.test("multi-level dropdown: parent closing modes on item selection", async (assert) => {
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
        <Dropdown>
          <t t-set-slot="menu">
            <Dropdown>
              <t t-set-slot="menu">
                <DropdownItem class="item1" parentClosingMode="'none'" />
                <DropdownItem class="item2" parentClosingMode="'closest'" />
                <DropdownItem class="item3" parentClosingMode="'all'" />
                <DropdownItem class="item4" />
              </t>
            </Dropdown>
          </t>
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
          <t t-set-slot="menu">
            <Dropdown t-on-dropdown-item-selected="onItemSelected">
              <t t-set-slot="menu">
                <DropdownItem payload="{ answer: 42 }" />
              </t>
            </Dropdown>
          </t>
        </Dropdown>
      `;
        env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        await click(parent.el, "button.o_dropdown_toggler:last-child");
        // As two listeners are defined in the template,
        // clicking once the item would execute the handler twice.
        await click(parent.el, "li");
    });

    QUnit.test("multi-level dropdown: recursive template can be rendered", async (assert) => {
        const recursiveTemplate = `
        <Dropdown startOpen="true">
          <t t-esc="name" />
          <t t-set-slot="menu">
            <t t-foreach="items" t-as="item">

              <t t-if="!item.children.length">
                <DropdownItem t-esc="item.name" />
              </t>

              <t t-else="" t-call="recursive.Template">
                <t t-set="name" t-value="item.name" />
                <t t-set="items" t-value="item.children" />
              </t>

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
            [...parent.el.querySelectorAll("button,li")].map((el) => el.textContent),
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
        assert.expect(20);
        class Parent extends owl.Component {
            onItemSelected(ev) {
                const { payload } = ev.detail;
                assert.step(payload.val.toString());
            }
        }
        Parent.template = owl.tags.xml`
        <Dropdown hotkey="'m'" t-on-dropdown-item-selected="onItemSelected">
          <t t-set-slot="menu">
            <DropdownItem class="item1" payload="{val:1}">item1</DropdownItem>
            <DropdownItem class="item2" hotkey="'2'" payload="{val:2}">item2</DropdownItem>
            <DropdownItem class="item3" payload="{val:3}">item3</DropdownItem>
          </t>
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
            ".o_dropdown_menu > .o_dropdown_active",
            "menu should not have any active items"
        );

        const scenarioSteps = [
            { hotkey: "arrowdown", expected: "item1" },
            { hotkey: "arrowdown", expected: "item2" },
            { hotkey: "arrowdown", expected: "item3" },
            { hotkey: "arrowdown", expected: "item3" },
            { hotkey: "arrowup", expected: "item2" },
            { hotkey: "arrowup", expected: "item1" },
            { hotkey: "arrowup", expected: "item1" },
            { hotkey: "shift+arrowdown", expected: "item3" },
            { hotkey: "shift+arrowup", expected: "item1" },
        ];

        for (const step of scenarioSteps) {
            triggerHotkey(step.hotkey);
            await nextTick();
            assert.hasClass(
                parent.el.querySelector(".o_dropdown_menu > .o_dropdown_active"),
                step.expected
            );
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
});
