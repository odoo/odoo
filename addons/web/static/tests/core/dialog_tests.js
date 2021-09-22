/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { Dialog } from "@web/core/dialog/dialog";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, nextTick } from "../helpers/utils";
import { makeFakeDialogService } from "../helpers/mock_services";

const { hooks, mount } = owl;
const { useRef, useState } = hooks;
const serviceRegistry = registry.category("services");
let parent;
let target;

class SimpleDialog extends Dialog {
    setup() {
        super.setup();
        this.title = "title" in this.props ? this.props.title : this.constructor.title;
        this.renderHeader =
            "renderHeader" in this.props ? this.props.renderHeader : this.constructor.renderHeader;
        this.renderFooter =
            "renderFooter" in this.props ? this.props.renderFooter : this.constructor.renderFooter;
        this.contentClass =
            "contentClass" in this.props ? this.props.contentClass : this.constructor.contentClass;
        this.size = "size" in this.props ? this.props.size : this.constructor.size;
        this.fullscreen =
            "fullscreen" in this.props ? this.props.fullscreen : this.constructor.fullscreen;
    }
}
SimpleDialog.bodyTemplate = owl.tags.xml`<t t-slot="default"/>`;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("dialog", makeFakeDialogService());
    });
    hooks.afterEach(() => {
        if (parent) {
            parent.unmount();
            parent = undefined;
        }
    });

    QUnit.module("Dialog");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(8);
        class Parent extends Dialog {}
        Parent.title = "Wow(l) Effect";
        Parent.bodyTemplate = owl.tags.xml`
            <t>
                Hello!
            </t>
            `;

        const env = await makeTestEnv();
        parent = await mount(Parent, { env, target, props: {} });
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
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
              <div>
                  <SimpleDialog title="'First Title'">
                      Hello!
                  </SimpleDialog>
                  <SimpleDialog title="'Second Title'">
                      Hello again!
                  </SimpleDialog>
              </div>
          `;
        Parent.components = { SimpleDialog };
        const env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
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
        const env = await makeTestEnv();
        class MyDialog extends SimpleDialog {}
        class Parent extends owl.Component {
            close() {
                assert.step("close");
            }
        }

        Parent.template = owl.tags.xml`
            <MyDialog close="close">
                Hello!
            </MyDialog>
        `;
        Parent.components = { MyDialog };
        parent = await mount(Parent, { env, target });
        assert.containsOnce(target, ".o_dialog");
        await click(target, ".o_dialog header button.close");
        assert.verifySteps(["close"]);
    });

    QUnit.test(
        "click on the default footer button triggers the service close",
        async function (assert) {
            const env = await makeTestEnv();
            assert.expect(3);
            class MyDialog extends SimpleDialog {}
            class Parent extends owl.Component {
                close() {
                    assert.step("close");
                }
            }

            Parent.template = owl.tags.xml`
                <MyDialog close="close">
                    Hello!
                </MyDialog>
            `;
            Parent.components = { MyDialog };
            parent = await mount(Parent, { env, target });
            assert.containsOnce(target, ".o_dialog");
            await click(target, ".o_dialog footer button");
            assert.verifySteps(["close"]);
        }
    );

    QUnit.test("render custom footer buttons is possible", async function (assert) {
        assert.expect(2);
        class SimpleButtonsDialog extends Dialog {}
        SimpleButtonsDialog.footerTemplate = owl.tags.xml`
            <div>
                <button class="btn btn-primary">The First Button</button>
                <button class="btn btn-primary">The Second Button</button>
            </div>
          `;
        class Parent extends owl.Component {
            constructor() {
                super(...arguments);
                this.state = useState({
                    displayDialog: true,
                });
            }
        }
        Parent.template = owl.tags.xml`
              <div>
                  <SimpleButtonsDialog/>
              </div>
          `;
        Parent.components = { SimpleButtonsDialog };
        const env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsOnce(target, ".o_dialog");
        assert.containsN(target, ".o_dialog footer button", 2);
    });

    QUnit.test("embed an arbitrary component in a dialog is possible", async function (assert) {
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
        Parent.components = { SimpleDialog, SubComponent };
        Parent.template = owl.tags.xml`
              <SimpleDialog>
                  <SubComponent text="'Wow(l) Effect'" t-on-subcomponent-clicked="_onSubcomponentClicked"/>
              </SimpleDialog>
          `;
        const env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsOnce(target, ".o_dialog");
        assert.containsOnce(target, ".o_dialog main .o_subcomponent");
        assert.strictEqual(target.querySelector(".o_subcomponent").textContent, "Wow(l) Effect");
        await click(target.querySelector(".o_subcomponent"));
        assert.verifySteps(["subcomponent-clicked", "message received by parent"]);
    });

    QUnit.test("dialog without header/footer", async function (assert) {
        assert.expect(4);
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
              <SimpleDialog renderHeader="false" renderFooter="false"/>
          `;
        const env = await makeTestEnv();
        Parent.components = { SimpleDialog };
        parent = await mount(Parent, { env, target });
        assert.containsOnce(target, ".o_dialog");
        assert.containsNone(target, ".o_dialog header");
        assert.containsOnce(target, "main", "a dialog has always a main node");
        assert.containsNone(target, ".o_dialog footer");
    });

    QUnit.test("dialog size can be chosen", async function (assert) {
        assert.expect(5);
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
      <div>
        <SimpleDialog contentClass="'xl'" size="'modal-xl'"/>
        <SimpleDialog contentClass="'lg'"/>
        <SimpleDialog contentClass="'md'" size="'modal-md'"/>
        <SimpleDialog contentClass="'sm'" size="'modal-sm'"/>
      </div>`;
        Parent.components = { SimpleDialog };
        const env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
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
        class Parent extends owl.Component {}
        Parent.template = owl.tags.xml`
              <div><SimpleDialog fullscreen="true"/></div>
          `;
        Parent.components = { SimpleDialog };
        const env = await makeTestEnv();
        parent = await mount(Parent, { env, target });
        assert.containsOnce(target, ".o_dialog");
        assert.hasClass(target.querySelector(".o_dialog .modal"), "o_modal_full");
    });

    QUnit.test("can be the UI active element", async function (assert) {
        assert.expect(3);
        class Parent extends owl.Component {
            setup() {
                this.ui = useService("ui");
                this.dialog = useRef("dialogRef");
                assert.strictEqual(
                    this.ui.activeElement,
                    document,
                    "UI active element should be the default (document) as Parent is not mounted yet"
                );
            }
            mounted() {
                const dialogModalEl = this.dialog.comp.modalRef.el;
                assert.strictEqual(
                    this.ui.activeElement,
                    dialogModalEl,
                    "UI active element should be the dialog modal"
                );
            }
        }
        const env = await makeTestEnv();
        Parent.template = owl.tags.xml`<div><SimpleDialog t-ref="dialogRef"/></div>`;
        Parent.components = { SimpleDialog };
        parent = await mount(Parent, { env, target });

        parent.unmount();
        assert.strictEqual(
            env.services.ui.activeElement,
            document,
            "UI owner should be reset to the default (document)"
        );
    });
});
