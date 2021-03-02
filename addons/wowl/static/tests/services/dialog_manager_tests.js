/** @odoo-module **/
import { click, getFixture, makeFakeRPCService, makeTestEnv, mount, nextTick } from "../helpers/index";
import { Registry } from "../../src/core/registry";
import { DialogContainer, dialogService } from "../../src/services/dialog_service";
import { Dialog } from "../../src/components/dialog/dialog";
import { notificationService } from '../../src/notifications/notification_service';
import { errorService } from '../../src/errors/error_service';
import { mainComponentRegistry } from "../../src/webclient/main_component_registry";

const { Component, tags } = owl;

let env;
let serviceRegistry;
let target;
let pseudoWebClient;

class PseudoWebClient extends Component {
  constructor() {
    super(...arguments);
    this.Components = odoo.mainComponentRegistry.getEntries();
  }
}
PseudoWebClient.template = tags.xml`
        <div>
            <div class="o_dialog_container"/>
            <div>
                <t t-foreach="Components" t-as="Component" t-key="Component[0]">
                    <t t-component="Component[1]"/>
                </t>
            </div>
        </div>
    `;

QUnit.module("DialogManager", {
  async beforeEach() {
    target = getFixture();
    serviceRegistry = new Registry();
    serviceRegistry.add(dialogService.name, dialogService);
    const componentRegistry = new Registry();
    componentRegistry.add("DialogContainer", mainComponentRegistry.get("DialogContainer"));
    env = await makeTestEnv({ serviceRegistry, mainComponentRegistry: componentRegistry });
  },
  afterEach() {
    pseudoWebClient.unmount();
  },
});
QUnit.test("Simple rendering with a single dialog", async (assert) => {
  var _a;
  assert.expect(9);
  class CustomDialog extends Component {}
  CustomDialog.template = tags.xml`<Dialog title="'Welcome'"/>`;
  CustomDialog.components = { Dialog };
  pseudoWebClient = await mount(PseudoWebClient, { target, env });
  assert.containsOnce(target, ".o_dialog_manager");
  assert.containsNone(target, ".o_dialog_manager portal");
  assert.containsNone(target, ".o_dialog_container .o_dialog");
  env.services[dialogService.name].open(CustomDialog);
  await nextTick();
  assert.containsOnce(target, ".o_dialog_manager portal");
  assert.containsOnce(target, ".o_dialog_container .o_dialog");
  assert.strictEqual(
    (_a = target.querySelector("header .modal-title")) === null || _a === void 0
      ? void 0
      : _a.textContent,
    "Welcome"
  );
  await click(target.querySelector(".o_dialog_container .o_dialog footer button"));
  assert.containsOnce(target, ".o_dialog_manager");
  assert.containsNone(target, ".o_dialog_manager portal");
  assert.containsNone(target, ".o_dialog_container .o_dialog");
});
QUnit.test("rendering with two dialogs", async (assert) => {
  var _a, _b;
  assert.expect(12);
  class CustomDialog extends Component {}
  CustomDialog.template = tags.xml`<Dialog title="props.title"/>`;
  CustomDialog.components = { Dialog };
  pseudoWebClient = await mount(PseudoWebClient, { target, env });
  assert.containsOnce(target, ".o_dialog_manager");
  assert.containsNone(target, ".o_dialog_manager portal");
  assert.containsNone(target, ".o_dialog_container .o_dialog");
  env.services[dialogService.name].open(CustomDialog, { title: "Hello" });
  await nextTick();
  assert.containsOnce(target, ".o_dialog_manager portal");
  assert.containsOnce(target, ".o_dialog_container .o_dialog");
  assert.strictEqual(
    (_a = target.querySelector("header .modal-title")) === null || _a === void 0
      ? void 0
      : _a.textContent,
    "Hello"
  );
  env.services[dialogService.name].open(CustomDialog, { title: "Sauron" });
  await nextTick();
  assert.containsN(target, ".o_dialog_manager portal", 2);
  assert.containsN(target, ".o_dialog_container .o_dialog", 2);
  assert.deepEqual(
    [...target.querySelectorAll("header .modal-title")].map((el) => el.textContent),
    ["Hello", "Sauron"]
  );
  await click(target.querySelector(".o_dialog_container .o_dialog footer button"));
  assert.containsOnce(target, ".o_dialog_manager portal");
  assert.containsOnce(target, ".o_dialog_container .o_dialog");
  assert.strictEqual(
    (_b = target.querySelector("header .modal-title")) === null || _b === void 0
      ? void 0
      : _b.textContent,
    "Sauron"
  );
});

QUnit.test("dialog component crashes", async (assert) => {
  assert.expect(4);

  class FailingDialog extends Component {
    setup() {
      throw new Error('Some Error');
    }
  }
  FailingDialog.template = tags.xml`<Dialog title="'Error'"/>`;
  FailingDialog.components =  { Dialog };

  const rpc = makeFakeRPCService();
  serviceRegistry.add(rpc.name, rpc);
  serviceRegistry.add(notificationService.name, notificationService);
  serviceRegistry.add(errorService.name, errorService);
  const componentRegistry = new Registry();
  componentRegistry.add("DialogContainer", DialogContainer)
  env = await makeTestEnv({ serviceRegistry, mainComponentRegistry: componentRegistry });

  pseudoWebClient = await mount(PseudoWebClient, { target, env });

  const qunitUnhandledReject = QUnit.onUnhandledRejection;
  QUnit.onUnhandledRejection = (reason) => {
    assert.step('error');
  };

  debugger;
  env.services[dialogService.name].open(FailingDialog);
  await nextTick();
  assert.verifySteps(['error']);
  assert.containsOnce(pseudoWebClient, '.modal');
  assert.containsOnce(pseudoWebClient, '.modal .o_dialog_error');

  QUnit.onUnhandledRejection = qunitUnhandledReject;
  pseudoWebClient.destroy();
});
