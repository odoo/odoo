/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { Dialog } from "@web/core/dialog/dialog";
import { makeTestEnv } from "../helpers/mock_env";
import { click, destroy, getFixture, mount } from "../helpers/utils";
import { makeFakeDialogService } from "../helpers/mock_services";

const { Component, useState, onMounted, xml } = owl;
const serviceRegistry = registry.category("services");
let parent;
let target;

async function makeDialogTestEnv() {
    const env = await makeTestEnv();
    env.dialogData = {
        isActive: true,
        close: () => {},
    };
    return env;
}

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("dialog", makeFakeDialogService());
    });
    hooks.afterEach(() => {
        if (parent) {
            parent = undefined;
        }
    });

    QUnit.module("Dialog");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(8);
        class Parent extends Component {}
        Parent.components = { Dialog };
        Parent.template = xml`
            <Dialog title="'Wow(l) Effect'">
                Hello!
            </Dialog>
            `;

        const env = await makeDialogTestEnv();
        parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_dialog");
        assert.containsOnce(
            target,
            ".o_dialog header .modal-title",
            "the header is rendered by default"
        );
        assert.strictEqual(
            target.querySelector("header .modal-title").textContent,
            "Wow(l) Effect"
        );
        assert.containsOnce(target, ".o_dialog main", "a dialog has always a main node");
        assert.strictEqual(target.querySelector("main").textContent, " Hello! ");
        assert.containsOnce(target, ".o_dialog footer", "the footer is rendered by default");
        assert.containsOnce(
            target,
            ".o_dialog footer button",
            "the footer is rendered with a single button 'Ok' by default"
        );
        assert.strictEqual(target.querySelector("footer button").textContent, "Ok");
    });

    QUnit.test("simple rendering with two dialogs", async function (assert) {
        assert.expect(3);
        class Parent extends Component {}
        Parent.template = xml`
              <div>
                  <Dialog title="'First Title'">
                      Hello!
                  </Dialog>
                  <Dialog title="'Second Title'">
                      Hello again!
                  </Dialog>
              </div>
          `;
        Parent.components = { Dialog };
        const env = await makeDialogTestEnv();
        parent = await mount(Parent, target, { env });
        assert.containsN(target, ".o_dialog", 2);
        assert.deepEqual(
            [...target.querySelectorAll("header .modal-title")].map((el) => el.textContent),
            ["First Title", "Second Title"]
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_dialog .modal-body")].map((el) => el.textContent),
            [" Hello! ", " Hello again! "]
        );
    });

    QUnit.test("click on the button x triggers the service close", async function (assert) {
        assert.expect(3);
        const env = await makeDialogTestEnv();
        env.dialogData.close = () => assert.step("close");

        class Parent extends Component {}
        Parent.template = xml`
            <Dialog>
                Hello!
            </Dialog>
        `;
        Parent.components = { Dialog };
        parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_dialog");
        await click(target, ".o_dialog header button.btn-close");
        assert.verifySteps(["close"]);
    });

    QUnit.test(
        "click on the default footer button triggers the service close",
        async function (assert) {
            const env = await makeDialogTestEnv();
            env.dialogData.close = () => assert.step("close");
            assert.expect(3);
            class Parent extends Component {}

            Parent.template = xml`
                <Dialog>
                    Hello!
                </Dialog>
            `;
            Parent.components = { Dialog };
            parent = await mount(Parent, target, { env });
            assert.containsOnce(target, ".o_dialog");
            await click(target, ".o_dialog footer button");
            assert.verifySteps(["close"]);
        }
    );

    QUnit.test("render custom footer buttons is possible", async function (assert) {
        assert.expect(2);
        class SimpleButtonsDialog extends Component {}
        SimpleButtonsDialog.components = { Dialog };
        SimpleButtonsDialog.template = xml`
            <Dialog>
                content
                <t t-set-slot="footer">
                    <div>
                        <button class="btn btn-primary">The First Button</button>
                        <button class="btn btn-primary">The Second Button</button>
                    </div>
                </t>
            </Dialog>
          `;
        class Parent extends Component {
            setup() {
                super.setup();
                this.state = useState({
                    displayDialog: true,
                });
            }
        }
        Parent.template = xml`
              <div>
                  <SimpleButtonsDialog/>
              </div>
          `;
        Parent.components = { SimpleButtonsDialog };
        const env = await makeDialogTestEnv();
        parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_dialog");
        assert.containsN(target, ".o_dialog footer button", 2);
    });

    QUnit.test("embed an arbitrary component in a dialog is possible", async function (assert) {
        assert.expect(6);
        class SubComponent extends Component {
            _onClick() {
                assert.step("subcomponent-clicked");
                this.props.onClicked();
            }
        }
        SubComponent.template = xml`
              <div class="o_subcomponent" t-esc="props.text" t-on-click="_onClick"/>
          `;
        class Parent extends Component {
            _onSubcomponentClicked() {
                assert.step("message received by parent");
            }
        }
        Parent.components = { Dialog, SubComponent };
        Parent.template = xml`
              <Dialog>
                  <SubComponent text="'Wow(l) Effect'" onClicked="_onSubcomponentClicked"/>
              </Dialog>
          `;
        const env = await makeDialogTestEnv();
        parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_dialog");
        assert.containsOnce(target, ".o_dialog main .o_subcomponent");
        assert.strictEqual(target.querySelector(".o_subcomponent").textContent, "Wow(l) Effect");
        await click(target.querySelector(".o_subcomponent"));
        assert.verifySteps(["subcomponent-clicked", "message received by parent"]);
    });

    QUnit.test("dialog without header/footer", async function (assert) {
        assert.expect(4);
        class Parent extends Component {}
        Parent.template = xml`
              <Dialog header="false" footer="false">content</Dialog>
          `;
        const env = await makeDialogTestEnv();
        Parent.components = { Dialog };
        parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_dialog");
        assert.containsNone(target, ".o_dialog header");
        assert.containsOnce(target, "main", "a dialog has always a main node");
        assert.containsNone(target, ".o_dialog footer");
    });

    QUnit.test("dialog size can be chosen", async function (assert) {
        assert.expect(5);
        class Parent extends Component {}
        Parent.template = xml`
      <div>
        <Dialog contentClass="'xl'" size="'xl'">content</Dialog>
        <Dialog contentClass="'lg'">content</Dialog>
        <Dialog contentClass="'md'" size="'md'">content</Dialog>
        <Dialog contentClass="'sm'" size="'sm'">content</Dialog>
      </div>`;
        Parent.components = { Dialog };
        const env = await makeDialogTestEnv();
        parent = await mount(Parent, target, { env });
        assert.containsN(target, ".o_dialog", 4);
        assert.containsOnce(
            target,
            target.querySelectorAll(".o_dialog .modal-dialog.modal-xl .xl")
        );
        assert.containsOnce(
            target,
            target.querySelectorAll(".o_dialog .modal-dialog.modal-lg .lg")
        );
        assert.containsOnce(
            target,
            target.querySelectorAll(".o_dialog .modal-dialog.modal-md .md")
        );
        assert.containsOnce(
            target,
            target.querySelectorAll(".o_dialog .modal-dialog.modal-sm .sm")
        );
    });

    QUnit.test("dialog can be rendered on fullscreen", async function (assert) {
        assert.expect(2);
        class Parent extends Component {}
        Parent.template = xml`
            <Dialog fullscreen="true">content</Dialog>
          `;
        Parent.components = { Dialog };
        const env = await makeDialogTestEnv();
        parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_dialog");
        assert.hasClass(target.querySelector(".o_dialog .modal"), "o_modal_full");
    });

    QUnit.test("can be the UI active element", async function (assert) {
        assert.expect(4);
        class Parent extends Component {
            setup() {
                this.ui = useService("ui");
                assert.strictEqual(
                    this.ui.activeElement,
                    document,
                    "UI active element should be the default (document) as Parent is not mounted yet"
                );
                onMounted(() => {
                    assert.containsOnce(target, ".modal");
                    assert.strictEqual(
                        this.ui.activeElement,
                        target.querySelector(".modal"),
                        "UI active element should be the dialog modal"
                    );
                });
            }
        }
        const env = await makeDialogTestEnv();
        Parent.template = xml`<Dialog>content</Dialog>`;
        Parent.components = { Dialog };

        const parent = await mount(Parent, target, { env });
        destroy(parent);

        assert.strictEqual(
            env.services.ui.activeElement,
            document,
            "UI owner should be reset to the default (document)"
        );
    });
});
