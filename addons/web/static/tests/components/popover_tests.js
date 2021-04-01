/** @odoo-module **/

import { triggerEvent, click, getFixture, makeTestEnv, nextTick } from "../helpers/index";
import { Popover } from "../../src/components/popover/popover";
import { patch, unpatch } from "../../src/utils/patch";
import { browser } from "../../src/core/browser";
import { registerCleanup } from "../helpers/cleanup";

const { Component, mount } = owl;
const { useState } = owl.hooks;
const { xml } = owl.tags;

let env;
let target;

function pointsTo(popover, element, position) {
  const hasCorrectClass = popover.classList.contains(`o_popover_${position}`);
  const expectedPosition = Popover.computePositioningData(popover, element)[position];
  const correctLeft =
    parseFloat(popover.style.left) === Math.round(expectedPosition.left * 100) / 100;
  const correctTop = parseFloat(popover.style.top) === Math.round(expectedPosition.top * 100) / 100;
  return hasCorrectClass && correctLeft && correctTop;
}

QUnit.module("Popover", {
  async beforeEach() {
    // todo: maybe add an "utils" function which do this and its cleanup??
    patch(browser, "mock:popover_tests", {
      setTimeout: (handler, _, ...args) => handler(...args),
      clearTimeout: () => {},
    });

    env = await makeTestEnv();
    target = getFixture();
    const popoverContainer = document.createElement("div");
    popoverContainer.classList.add("o_popover_container");
    target.appendChild(popoverContainer);

    registerCleanup(() => {
      unpatch(browser, "mock:popover_tests");
      target.removeChild(popoverContainer);
    });
  },
});

QUnit.test("Simple rendering", async function (assert) {
  assert.expect(6);

  class Parent extends Component {}
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-center">
      <button id="close">Click me to close</button>
      <Popover>
        <button id="open">Click me to open</button>
        <t t-set-slot="content">
          Popover
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });

  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  await click(target, "#open");

  assert.containsOnce(target, ".o_popover", "Should contain one popover");

  const popover = target.querySelector(".o_popover");
  assert.hasClass(popover, "o_popover_bottom", "The popover should have a bottom position");
  assert.strictEqual(
    popover.textContent.trim(),
    "Popover",
    "The popover's content should be 'Popover'"
  );
  assert.ok(pointsTo(popover, target.querySelector("#open"), "bottom"));

  await click(target, "#close");
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  parent.destroy();
});

QUnit.test("Recompute position", async function (assert) {
  assert.expect(4);

  class Parent extends Component {
    setup() {
      this.state = useState({
        position: "bottom",
      });
    }
  }
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-center">
      <button id="close">Click me to close</button>
      <Popover position="state.position">
        <button id="open">Click me to open</button>
        <t t-set-slot="content">
          Popover
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });

  await click(target, "#open");

  const popover = target.querySelector(".o_popover");
  assert.ok(pointsTo(popover, target.querySelector("#open"), "bottom"));

  parent.state.position = "left";
  await nextTick();
  assert.ok(pointsTo(popover, target.querySelector("#open"), "left"));

  parent.state.position = "right";
  await nextTick();
  assert.ok(pointsTo(popover, target.querySelector("#open"), "right"));

  parent.state.position = "top";
  await nextTick();
  assert.ok(pointsTo(popover, target.querySelector("#open"), "top"));

  parent.destroy();
});

QUnit.test("Show popover on hover", async function (assert) {
  assert.expect(4);

  class Parent extends Component {}
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-start">
      <Popover trigger="'hover'">
        <button id="open">Hover me to open</button>
        <t t-set-slot="content">
          Popover
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  await triggerEvent(target, "#open", "mouseenter", { bubbles: true });

  assert.containsOnce(target, ".o_popover", "Should contain one popover");
  const popover = target.querySelector(".o_popover");
  assert.ok(pointsTo(popover, target.querySelector("#open"), "bottom"));

  await triggerEvent(target, "#open", "mouseleave", { bubbles: true });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  parent.destroy();
});

QUnit.test("Show popover manually", async function (assert) {
  assert.expect(4);

  class Parent extends Component {
    setup() {
      this.state = useState({
        showPopover: false,
      });
    }
  }
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-start">
      <Popover t-if="state.showPopover" trigger="'none'">
        <div id="target">Target</div>
        <t t-set-slot="content">
          Popover
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  parent.state.showPopover = true;
  await nextTick();
  assert.containsOnce(target, ".o_popover", "Should contain one popover");
  const popover = target.querySelector(".o_popover");
  assert.ok(pointsTo(popover, target.querySelector("#target"), "bottom"));

  parent.state.showPopover = false;
  await nextTick();
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  parent.destroy();
});

QUnit.test("Multiple popovers", async function (assert) {
  assert.expect(8);

  class Parent extends Component {}
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-start">
      <button id="close">Click me to close</button>
      <Popover>
        <button id="open1">Open 1</button>
        <t t-set-slot="content">
          <div id="popover1">Popover 1</div>
        </t>
      </Popover>
      <Popover>
        <button id="open2">Open 2</button>
        <t t-set-slot="content">
          <div id="popover2">Popover 2</div>
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  await click(target, "#open1");
  assert.containsOnce(target, "#popover1", "Should contain popover 1");
  assert.containsNone(target, "#popover2", "Should not contain popover 2");
  let popover = target.querySelector(".o_popover");
  assert.ok(pointsTo(popover, target.querySelector("#open1"), "bottom"));

  await click(target, "#open2");
  assert.containsNone(target, "#popover1", "Should not contain popover 1");
  assert.containsOnce(target, "#popover2", "Should contain popover 2");
  popover = target.querySelector(".o_popover");
  assert.ok(pointsTo(popover, target.querySelector("#open2"), "bottom"));

  await click(target, "#close");
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  parent.destroy();
});

QUnit.test("Close event", async function (assert) {
  assert.expect(3);

  class Content extends Component {}
  Content.template = xml`
    <button id="close" t-on-click="trigger('popover-closed')">Close</button>
  `;

  class Parent extends Component {}
  Parent.components = { Content, Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-start">
      <Popover>
        <button id="open">Open</button>
        <t t-set-slot="content">
          <Content />
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  await click(target, "#open");
  assert.containsOnce(target, ".o_popover", "Should contain one popover");

  await click(target, "#close");
  assert.containsNone(target, ".o_popover", "Popover should be closed");

  parent.destroy();
});

QUnit.test("Target click", async function (assert) {
  assert.expect(4);

  class Parent extends Component {}
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-start">
      <button id="toggle">Toggle</button>
      <Popover target="'#toggle'">
        <t t-set-slot="content">
          Popover
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  await click(target, "#toggle");
  assert.containsOnce(target, ".o_popover", "Should contain one popover");
  const popover = target.querySelector(".o_popover");
  assert.ok(pointsTo(popover, target.querySelector("#toggle"), "bottom"));

  await click(target, "#toggle");
  assert.containsNone(target, ".o_popover", "Popover should be closed");

  parent.destroy();
});

QUnit.test("close popover when target is removed", async function (assert) {
  assert.expect(3);

  class Parent extends Component {}
  Parent.components = { Popover };
  Parent.template = xml`
    <div class="d-flex h-25 justify-content-around align-items-start">
      <button id="target">target</button>
      <Popover target="'#target'">
        <t t-set-slot="content">
          Popover
        </t>
      </Popover>
    </div>
  `;

  const parent = await mount(Parent, { env, target });
  assert.containsNone(target, ".o_popover", "Should not contain any popover");

  await click(target, "#target");
  assert.containsOnce(target, ".o_popover", "Should contain one popover");

  target.querySelector("#target").remove();
  await nextTick();
  assert.containsNone(target, ".o_popover", "Popover should be closed");

  parent.destroy();
});
