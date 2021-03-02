/** @odoo-module **/

import { Dropdown } from "../../src/components/dropdown/dropdown";
import { DropdownItem } from "../../src/components/dropdown/dropdown_item";
import { click, makeTestEnv, mount, nextTick } from "../helpers/utility";
import { makeDeferred } from "../helpers/index";

let env;
let parent;

QUnit.module("Dropdown", {
  async beforeEach() {
    env = await makeTestEnv();
  },
  async afterEach() {
    parent.unmount();
  },
});

QUnit.test("can be rendered", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown };
  Parent.template = owl.tags.xml`<Dropdown/>`;
  parent = await mount(Parent, { env });
  assert.containsOnce(parent.el, "button.o_dropdown_toggler");
  assert.containsNone(parent.el, "ul.o_dropdown_menu");
});

QUnit.test("can be styled", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown, DropdownItem };
  Parent.template = owl.tags.xml`
      <Dropdown class="one" togglerClass="'two'" menuClass="'three'">
        <t t-set-slot="menu">
          <DropdownItem class="four" />
        </t>
      </Dropdown>
    `;
  parent = await mount(Parent, { env });
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
  Parent.components = { Dropdown };
  Parent.template = owl.tags.xml`<Dropdown beforeOpen="beforeOpen"/>`;
  parent = await mount(Parent, { env });
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
  Parent.components = { Dropdown };
  Parent.template = owl.tags.xml`<Dropdown startOpen="true" beforeOpen="beforeOpen"/>`;
  parent = await mount(Parent, { env });
  assert.verifySteps(["beforeOpen"]);
  assert.containsOnce(parent.el, "ul.o_dropdown_menu");
});

QUnit.test("close on outside click", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown };
  Parent.template = owl.tags.xml`
      <div>
        <div class="outside">outside</div>
        <Dropdown/>
      </div>
    `;
  parent = await mount(Parent, { env });
  await click(parent.el, "button.o_dropdown_toggler");
  assert.containsOnce(parent.el, "ul.o_dropdown_menu");
  await click(parent.el, "div.outside");
  assert.containsNone(parent.el, "ul.o_dropdown_menu");
});

QUnit.test("close on item selection", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown, DropdownItem };
  Parent.template = owl.tags.xml`
      <Dropdown>
        <t t-set-slot="menu">
          <DropdownItem/>
        </t>
      </Dropdown>
    `;
  parent = await mount(Parent, { env });
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
  Parent.components = { Dropdown, DropdownItem };
  Parent.template = owl.tags.xml`
      <Dropdown t-on-dropdown-item-selected="onItemSelected">
        <t t-set-slot="menu">
          <DropdownItem payload="{ answer: 42 }"/>
        </t>
      </Dropdown>
    `;
  parent = await mount(Parent, { env });
  await click(parent.el, "button.o_dropdown_toggler");
  await click(parent.el, "ul.o_dropdown_menu li");
});

QUnit.test("multi-level dropdown: can be rendered and toggled", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown };
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
  parent = await mount(Parent, { env });
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
});

QUnit.test("multi-level dropdown: initial open state can be true", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown };
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
  parent = await mount(Parent, { env });
  assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
});

QUnit.test("multi-level dropdown: close on outside click", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown };
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
  parent = await mount(Parent, { env });
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  assert.containsN(parent.el, "ul.o_dropdown_menu", 3);
  await click(parent.el, "div.outside");
  assert.containsNone(parent.el, "ul.o_dropdown_menu");
});

QUnit.test("multi-level dropdown: close on item selection", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown, DropdownItem };
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
  parent = await mount(Parent, { env });
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  await click(parent.el, "button.o_dropdown_toggler:last-child");
  assert.containsN(parent.el, "ul.o_dropdown_menu", 2);
  await click(parent.el, "li");
  assert.containsNone(parent.el, "ul.o_dropdown_menu");
});

QUnit.test("multi-level dropdown: parent closing modes on item selection", async (assert) => {
  class Parent extends owl.Component {}
  Parent.components = { Dropdown, DropdownItem };
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
  parent = await mount(Parent, { env });
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
  Parent.components = { Dropdown, DropdownItem };
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
  parent = await mount(Parent, { env });
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
  env.qweb.addTemplate("recursive.Template", recursiveTemplate);
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
  Parent.components = { Dropdown, DropdownItem };
  Parent.template = "recursive.Template";
  parent = await mount(Parent, { env });
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
    Parent.components = { Dropdown };
    Parent.template = owl.tags.xml`
      <div>
        <Dropdown class="one" />
        <Dropdown class="two" beforeOpen="beforeOpen"/>
        <Dropdown class="three" />
        <div class="outside">OUTSIDE</div>
      </div>
    `;
    parent = await mount(Parent, { env });
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
    Parent.components = { Dropdown };
    Parent.template = owl.tags.xml`
      <div>
        <div><Dropdown class="foo" /></div>
        <Dropdown class="bar1" />
        <Dropdown class="bar2" />
      </div>
    `;
    parent = await mount(Parent, { env });
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
    Parent.components = { Dropdown };
    Parent.template = owl.tags.xml`
      <div>
        <div><Dropdown class="foo" /></div>
        <Dropdown class="bar1" />
        <Dropdown class="bar2" />
      </div>
    `;
    parent = await mount(Parent, { env });
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
