/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBoxDropdownItem } from "@web/core/dropdown/checkbox_dropdown_item";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import {
    click,
    getFixture,
    makeDeferred,
    mount,
    mouseEnter,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../helpers/utils";
import { makeParent } from "./tooltip/tooltip_service_tests";

const { App, Component, xml } = owl;
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
            '<div class="o-dropdown dropdown o-dropdown--no-caret"><button class="dropdown-toggle"></button></div>'
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
            '<span class="dropdown-item">coucou</span>'
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
            '<a class="dropdown-item" href="#">coucou</a>'
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
        assert.expect(5);
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
        beforeOpenProm.resolve();
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        await click(target, "button.dropdown-toggle");
        assert.containsNone(target, ".dropdown-menu");
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
                this._super();
            }
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
            templates: window.__OWL_TEMPLATES__,
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

    QUnit.test("siblings dropdowns with manualOnly props", async (assert) => {
        assert.expect(7);
        class Parent extends Component {}
        Parent.template = xml`
        <div>
          <Dropdown class="'one'" manualOnly="true"/>
          <Dropdown class="'two'" manualOnly="true"/>
          <div class="outside">OUTSIDE</div>
        </div>
      `;
        Parent.components = { Dropdown };
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        // Click on one
        await click(target, ".one button");
        assert.containsOnce(target, ".dropdown-menu");
        // Click on two
        await click(target, ".two button");
        assert.containsN(target, ".dropdown-menu", 2);
        // Click on one again
        await click(target, ".one button");
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsNone(target.querySelector(".one"), ".dropdown-menu");
        // Hover on one
        const one = target.querySelector(".one");
        one.querySelector("button").dispatchEvent(new MouseEvent("mouseenter"));
        await nextTick();
        assert.containsOnce(target, ".dropdown-menu");
        assert.containsNone(target.querySelector(".one"), ".dropdown-menu");
        // Click outside
        await click(target, "div.outside");
        assert.containsOnce(target, ".dropdown-menu");
    });

    QUnit.test("dropdowns keynav", async (assert) => {
        assert.expect(26);
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
        await click(target, ".my_custom_toggler");
        assert.containsOnce(target, ".dropdown .dropdown-menu");
        assert.containsN(target, ".dropdown .dropdown-menu .dropdown-item", 2);
    });

    QUnit.test("multi-level dropdown: keynav", async (assert) => {
        assert.expect(125);
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
                const remove = this._super(...arguments);
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

    QUnit.skipWOWL(
        "click on the label of a CheckBoxDropdownItem selects it once",
        async (assert) => {
            // skipWOWL
            assert.expect(2);
            class Parent extends owl.Component {
                onSelected() {
                    assert.step("selected");
                }
            }
            Parent.components = { CheckBoxDropdownItem, Dropdown };
            Parent.template = owl.xml`
            <Dropdown>
                <CheckBoxDropdownItem onSelected.bind="onSelected"/>
            </Dropdown>
        `;
            env = await makeTestEnv();
            parent = await mount(Parent, target, { env });
            await click(parent.el, "button.dropdown-toggle");
            await click(parent.el, ".dropdown-item label");
            assert.verifySteps(["selected"]);
        }
    );

    QUnit.test("Dropdown with a tooltip", async (assert) => {
        assert.expect(2);

        class MyComponent extends owl.Component {}
        MyComponent.template = owl.xml`
            <Dropdown tooltip="'My tooltip'">
                <DropdownItem/>
            </Dropdown>`;
        MyComponent.components = { Dropdown };

        await makeParent(MyComponent);
        await mouseEnter(target, "button.dropdown-toggle");
        assert.containsOnce(target, ".o-tooltip");
        assert.strictEqual(target.querySelector(".o-tooltip").textContent, "My tooltip");
    });
});
