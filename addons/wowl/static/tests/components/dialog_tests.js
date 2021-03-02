/** @odoo-module **/
const { hooks } = owl;
const { useState } = hooks;
import { Dialog } from "../../src/components/dialog/dialog";
import { click, getFixture, makeTestEnv, mount, nextTick } from "../helpers/index";
let parent;
let target;
let env;
QUnit.module("Dialog", {
  async beforeEach() {
    target = getFixture();
    const dialogContainer = document.createElement("div");
    dialogContainer.classList.add("o_dialog_container");
    target.append(dialogContainer);
    env = await makeTestEnv();
  },
  async afterEach() {
    if (parent) {
      parent.unmount();
    }
  },
});
QUnit.test("simple rendering", async function (assert) {
  var _a, _b, _c;
  assert.expect(8);
  class Parent extends owl.Component {}
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <Dialog title="'Wow(l) Effect'">
                Hello!
            </Dialog>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsOnce(target, "div.o_dialog_container .o_dialog");
  assert.containsOnce(target, ".o_dialog header .modal-title", "the header is rendered by default");
  assert.strictEqual(
    (_a = target.querySelector("header .modal-title")) === null || _a === void 0
      ? void 0
      : _a.textContent,
    "Wow(l) Effect"
  );
  assert.containsOnce(target, ".o_dialog main", "a dialog has always a main node");
  assert.strictEqual(
    (_b = target.querySelector("main")) === null || _b === void 0 ? void 0 : _b.textContent,
    " Hello! "
  );
  assert.containsOnce(target, ".o_dialog footer", "the footer is rendered by default");
  assert.containsOnce(
    target,
    ".o_dialog footer button",
    "the footer is rendered with a single button 'Ok' by default"
  );
  assert.strictEqual(
    (_c = target.querySelector("footer button")) === null || _c === void 0
      ? void 0
      : _c.textContent,
    "Ok"
  );
});
QUnit.test("simple rendering with two dialogs", async function (assert) {
  assert.expect(2);
  class Parent extends owl.Component {}
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <div>
                <Dialog title="'First Title'">
                    Hello!
                </Dialog>
                <Dialog title="'Second Title'">
                    Hello again!
                </Dialog>
            </div>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsN(target, ".o_dialog", 2);
  assert.deepEqual(
    [...target.querySelectorAll(".o_dialog .modal-body")].map((el) => el.textContent),
    [" Hello again! ", " Hello! "] // mounted is called in reverse order
  );
});
QUnit.test("click on the button x triggers the custom event 'dialog-closed'", async function (
  assert
) {
  assert.expect(2);
  class Parent extends owl.Component {
    constructor() {
      super(...arguments);
      this.state = useState({
        displayDialog: true,
      });
    }
  }
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <div t-on-dialog-closed="state.displayDialog = false">
                <Dialog t-if="state.displayDialog">
                    Hello!
                </Dialog>
            </div>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsOnce(target, ".o_dialog");
  await click(target, ".o_dialog header button.close");
  assert.containsNone(target, ".o_dialog");
});
QUnit.test(
  "click on the default footer button triggers the custom event 'dialog-closed'",
  async function (assert) {
    assert.expect(2);
    class Parent extends owl.Component {
      constructor() {
        super(...arguments);
        this.state = useState({
          displayDialog: true,
        });
      }
    }
    Parent.components = { Dialog };
    Parent.template = owl.tags.xml`
            <div t-on-dialog-closed="state.displayDialog = false">
                <Dialog t-if="state.displayDialog">
                    Hello!
                </Dialog>
            </div>
        `;
    parent = await mount(Parent, { env, target });
    assert.containsOnce(target, ".o_dialog");
    await click(target, ".o_dialog footer button");
    assert.containsNone(target, ".o_dialog");
  }
);
QUnit.test("render custom footer buttons is possible", async function (assert) {
  assert.expect(3);
  class Parent extends owl.Component {
    constructor() {
      super(...arguments);
      this.state = useState({
        displayDialog: true,
      });
    }
  }
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <div>
                <Dialog t-if="state.displayDialog">
                    <t t-set="buttons">
                        <button class="btn btn-primary" t-on-click="state.displayDialog = false">The First Button</button>
                        <button class="btn btn-primary">The Second Button</button>
                    </t>
                </Dialog>
            </div>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsOnce(target, ".o_dialog");
  assert.containsN(target, ".o_dialog footer button", 2);
  await click(target.querySelector(".o_dialog footer button"));
  assert.containsNone(target, ".o_dialog");
});
QUnit.test("embed an arbitrary component in a dialog is possible", async function (assert) {
  var _a;
  assert.expect(6);
  class SubComponent extends owl.Component {
    _onClick() {
      assert.step("subcomponent-clicked");
      this.trigger("subcomponent-clicked");
    }
  }
  SubComponent.template = owl.tags.xml`
            <div class="o_subcomponent" t-esc="props.text" t-on-click="_onClick"/>
        `;
  class Parent extends owl.Component {
    _onSubcomponentClicked() {
      assert.step("message received by parent");
    }
  }
  Parent.components = { Dialog, SubComponent };
  Parent.template = owl.tags.xml`
            <Dialog>
                <SubComponent text="'Wow(l) Effect'" t-on-subcomponent-clicked="_onSubcomponentClicked"/>
            </Dialog>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsOnce(target, ".o_dialog");
  assert.containsOnce(target, ".o_dialog main .o_subcomponent");
  assert.strictEqual(
    (_a = target.querySelector(".o_subcomponent")) === null || _a === void 0
      ? void 0
      : _a.textContent,
    "Wow(l) Effect"
  );
  await click(target.querySelector(".o_subcomponent"));
  assert.verifySteps(["subcomponent-clicked", "message received by parent"]);
});
QUnit.test("dialog without header/footer", async function (assert) {
  assert.expect(4);
  class Parent extends owl.Component {}
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <Dialog renderHeader="false" renderFooter="false"/>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsOnce(target, ".o_dialog");
  assert.containsNone(target, ".o_dialog header");
  assert.containsOnce(target, "main", "a dialog has always a main node");
  assert.containsNone(target, ".o_dialog footer");
});
QUnit.test("dialog size can be chosen", async function (assert) {
  assert.expect(5);
  class Parent extends owl.Component {}
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
    <div>
      <Dialog contentClass="'xl'" size="'modal-xl'"/>
      <Dialog contentClass="'lg'"/>
      <Dialog contentClass="'md'" size="'modal-md'"/>
      <Dialog contentClass="'sm'" size="'modal-sm'"/>
    </div>`;
  parent = await mount(Parent, { env, target });
  assert.containsN(target, ".o_dialog", 4);
  assert.containsOnce(target, target.querySelectorAll(".o_dialog .modal-dialog.modal-xl .xl"));
  assert.containsOnce(target, target.querySelectorAll(".o_dialog .modal-dialog.modal-lg .lg"));
  assert.containsOnce(target, target.querySelectorAll(".o_dialog .modal-dialog.modal-md .md"));
  assert.containsOnce(target, target.querySelectorAll(".o_dialog .modal-dialog.modal-sm .sm"));
});
QUnit.test("dialog can be rendered on fullscreen", async function (assert) {
  assert.expect(2);
  class Parent extends owl.Component {}
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <div><Dialog fullscreen="true"/></div>
        `;
  parent = await mount(Parent, { env, target });
  assert.containsOnce(target, ".o_dialog");
  assert.hasClass(target.querySelector(".o_dialog .modal"), "o_modal_full");
});
QUnit.test("Interactions between multiple dialogs", async function (assert) {
  assert.expect(14);
  class Parent extends owl.Component {
    constructor() {
      super(...arguments);
      this.dialogIds = useState({});
    }
    _onDialogClosed(id) {
      assert.step(`dialog_id=${id}_closed`);
      delete this.dialogIds[id];
    }
  }
  Parent.components = { Dialog };
  Parent.template = owl.tags.xml`
            <div>
              <Dialog t-foreach="Object.keys(dialogIds)" t-as="dialogId" t-key="dialogId"
                t-on-dialog-closed="_onDialogClosed(dialogId)"
                />
            </div>
        `;
  const parent = await mount(Parent, { env, target });
  parent.dialogIds[0] = 1;
  await nextTick();
  parent.dialogIds[1] = 1;
  await nextTick();
  parent.dialogIds[2] = 1;
  await nextTick();
  function activity(modals) {
    const res = [];
    for (let i = 0; i < modals.length; i++) {
      res[i] = !modals[i].classList.contains("o_inactive_modal");
    }
    return res;
  }
  let modals = document.querySelectorAll(".modal");
  assert.containsN(target, ".o_dialog", 3);
  assert.deepEqual(activity(modals), [false, false, true]);
  assert.hasClass(target.querySelector(".o_dialog_container"), "modal-open");
  let lastDialog = modals[modals.length - 1];
  lastDialog.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
  await nextTick();
  await nextTick();
  modals = document.querySelectorAll(".modal");
  assert.containsN(target, ".o_dialog", 2);
  assert.deepEqual(activity(modals), [false, true]);
  assert.hasClass(target.querySelector(".o_dialog_container"), "modal-open");
  lastDialog = modals[modals.length - 1];
  await click(lastDialog, "footer button");
  modals = document.querySelectorAll(".modal");
  assert.containsN(target, ".o_dialog", 1);
  assert.deepEqual(activity(modals), [true]);
  assert.hasClass(target.querySelector(".o_dialog_container"), "modal-open");
  parent.unmount();
  // dialog 0 is closed through the removal of its parent => no callback
  assert.containsNone(target, ".o_dialog_container .modal");
  assert.doesNotHaveClass(target.querySelector(".o_dialog_container"), "modal-open");
  assert.verifySteps(["dialog_id=2_closed", "dialog_id=1_closed"]);
});
