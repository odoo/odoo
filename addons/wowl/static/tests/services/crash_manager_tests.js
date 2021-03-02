/** @odoo-module **/
const { Component, tags } = owl;
import { Registry } from "../../src/core/registry";
import { crashManagerService } from "../../src/crash_manager/crash_manager_service";
import { notificationService } from "../../src/notifications/notification_service";
import { RPCErrorDialog } from "../../src/crash_manager/error_dialogs";
import { dialogService } from "../../src/services/dialog_service";
import { makeFakeRPCService, makeFakeNotificationService } from "../helpers/mocks";
import { ConnectionLostError, RPCError } from "../../src/services/rpc";
import { nextTick } from "../helpers/utility";
import { makeTestEnv } from "../helpers/index";

function makeFakeDialogService(open) {
  return {
    name: "dialog",
    deploy() {
      return { open };
    },
  };
}

let serviceRegistry;
let windowAddEventListener = window.addEventListener;

QUnit.module("CrashManager", {
  async beforeEach() {
    serviceRegistry = new Registry();
    serviceRegistry.add(crashManagerService.name, crashManagerService);
    serviceRegistry.add(dialogService.name, dialogService);
    serviceRegistry.add(notificationService.name, notificationService);
    serviceRegistry.add("rpc", makeFakeRPCService());
  },
  afterEach() {
    window.addEventListener = windowAddEventListener;
  },
});
QUnit.test("handle RPC_ERROR of type='server' and no associated dialog class", async (assert) => {
  assert.expect(2);
  let errorCb;
  window.addEventListener = (type, cb) => {
    if (type === "unhandledrejection") {
      errorCb = cb;
    }
  };
  const error = new RPCError();
  error.code = 701;
  error.message = "Some strange error occured";
  error.data = { debug: "somewhere" };
  error.subType = "strange_error";
  function open(dialogClass, props) {
    assert.strictEqual(dialogClass, RPCErrorDialog);
    assert.deepEqual(props, {
      name: "RPC_ERROR",
      type: "server",
      code: 701,
      data: {
        debug: "somewhere",
      },
      subType: "strange_error",
      message: "Some strange error occured",
      exceptionName: undefined,
      traceback: error.stack,
    });
  }
  serviceRegistry.add("dialog", makeFakeDialogService(open), true);
  await makeTestEnv({ serviceRegistry });
  const errorEvent = new PromiseRejectionEvent("error", { reason: error, promise: null });
  errorCb(errorEvent);
});
QUnit.test(
  "handle RPC_ERROR of type='server' and associated custom dialog class",
  async (assert) => {
    assert.expect(2);
    let errorCb;
    window.addEventListener = (type, cb) => {
      if (type === "unhandledrejection") {
        errorCb = cb;
      }
    };
    class CustomDialog extends Component {}
    CustomDialog.template = tags.xml`<RPCErrorDialog title="'Strange Error'"/>`;
    CustomDialog.components = { RPCErrorDialog };
    const error = new RPCError();
    error.code = 701;
    error.message = "Some strange error occured";
    error.Component = CustomDialog;
    function open(dialogClass, props) {
      assert.strictEqual(dialogClass, CustomDialog);
      assert.deepEqual(props, {
        name: "RPC_ERROR",
        type: "server",
        code: 701,
        data: undefined,
        subType: undefined,
        message: "Some strange error occured",
        exceptionName: undefined,
        traceback: error.stack,
      });
    }
    serviceRegistry.add("dialog", makeFakeDialogService(open), true);
    await makeTestEnv({ serviceRegistry });
    odoo.errorDialogRegistry.add("strange_error", CustomDialog);
    const errorEvent = new PromiseRejectionEvent("error", { reason: error, promise: null });
    errorCb(errorEvent);
  }
);
QUnit.test("handle CONNECTION_LOST_ERROR", async (assert) => {
  let errorCb;
  window.addEventListener = (type, cb) => {
    if (type === "unhandledrejection") {
      errorCb = cb;
    }
  };
  const mockBrowser = {
    setTimeout: (callback, delay) => {
      assert.step(`set timeout (${delay === 2000 ? delay : ">2000"})`);
      callback();
    },
  };
  const mockCreate = (message) => {
    assert.step(`create (${message})`);
    return 1234;
  };
  const mockClose = (id) => assert.step(`close (${id})`);
  serviceRegistry.add("notification", makeFakeNotificationService(mockCreate, mockClose), true);
  const values = [false, true]; // simulate the 'back online status' after 2 'version_info' calls
  const mockRPC = async (route) => {
    if (route === "/web/webclient/version_info") {
      assert.step("version_info");
      const online = values.shift();
      if (online) {
        return Promise.resolve(true);
      } else {
        return Promise.reject();
      }
    }
  };
  await makeTestEnv({ serviceRegistry, mockRPC, browser: mockBrowser });
  const error = new ConnectionLostError();
  const errorEvent = new PromiseRejectionEvent("error", { reason: error, promise: null });
  errorCb(errorEvent);
  await nextTick(); // wait for mocked RPCs
  assert.verifySteps([
    "create (Connection lost. Trying to reconnect...)",
    "set timeout (2000)",
    "version_info",
    "set timeout (>2000)",
    "version_info",
    "close (1234)",
    "create (Connection restored. You are back online.)",
  ]);
});
