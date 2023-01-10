/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import {
    ClientErrorDialog,
    RPCErrorDialog,
    NetworkErrorDialog,
} from "@web/core/errors/error_dialogs";
import { errorService, UncaughtPromiseError } from "@web/core/errors/error_service";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { registerCleanup } from "../../helpers/cleanup";
import { makeTestEnv } from "../../helpers/mock_env";
import {
    makeFakeDialogService,
    makeFakeLocalizationService,
    makeFakeNotificationService,
    makeFakeRPCService,
} from "../../helpers/mock_services";
import { getFixture, makeDeferred, mount, nextTick, patchWithCleanup } from "../../helpers/utils";

import { Component, xml, onError, OwlError, onWillStart } from "@odoo/owl";
const errorDialogRegistry = registry.category("error_dialogs");
const errorHandlerRegistry = registry.category("error_handlers");
const serviceRegistry = registry.category("services");

let errorCb;
let unhandledRejectionCb;

QUnit.module("Error Service", {
    async beforeEach() {
        serviceRegistry.add("error", errorService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("rpc", makeFakeRPCService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        const windowAddEventListener = browser.addEventListener;
        browser.addEventListener = (type, cb) => {
            if (type === "unhandledrejection") {
                unhandledRejectionCb = (ev) => {
                    ev.preventDefault();
                    cb(ev);
                };
            }
            if (type === "error") {
                errorCb = (ev) => {
                    ev.preventDefault();
                    cb(ev);
                };
            }
        };
        registerCleanup(() => {
            browser.addEventListener = windowAddEventListener;
        });
    },
});

QUnit.test("handle RPC_ERROR of type='server' and no associated dialog class", async (assert) => {
    assert.expect(2);
    const error = new RPCError();
    error.code = 701;
    error.message = "Some strange error occured";
    error.data = { debug: "somewhere" };
    error.subType = "strange_error";
    function addDialog(dialogClass, props) {
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
            exceptionName: null,
            traceback: error.stack,
        });
    }
    serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
    await makeTestEnv();
    const errorEvent = new PromiseRejectionEvent("error", {
        reason: error,
        promise: null,
        cancelable: true,
    });
    await unhandledRejectionCb(errorEvent);
});

QUnit.test(
    "handle custom RPC_ERROR of type='server' and associated custom dialog class",
    async (assert) => {
        assert.expect(2);
        class CustomDialog extends Component {}
        CustomDialog.template = xml`<RPCErrorDialog title="'Strange Error'"/>`;
        CustomDialog.components = { RPCErrorDialog };
        const error = new RPCError();
        error.code = 701;
        error.message = "Some strange error occured";
        const errorData = {
            context: { exception_class: "strange_error" },
            name: "strange_error",
        };
        error.data = errorData;
        function addDialog(dialogClass, props) {
            assert.strictEqual(dialogClass, CustomDialog);
            assert.deepEqual(props, {
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "Some strange error occured",
                exceptionName: null,
                traceback: error.stack,
            });
        }
        serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
        await makeTestEnv();
        errorDialogRegistry.add("strange_error", CustomDialog);
        const errorEvent = new PromiseRejectionEvent("error", {
            reason: error,
            promise: null,
            cancelable: true,
        });
        await unhandledRejectionCb(errorEvent);
    }
);

QUnit.test(
    "handle normal RPC_ERROR of type='server' and associated custom dialog class",
    async (assert) => {
        assert.expect(2);
        class CustomDialog extends Component {}
        CustomDialog.template = xml`<RPCErrorDialog title="'Strange Error'"/>`;
        CustomDialog.components = { RPCErrorDialog };
        class NormalDialog extends Component {}
        NormalDialog.template = xml`<RPCErrorDialog title="'Normal Error'"/>`;
        NormalDialog.components = { RPCErrorDialog };
        const error = new RPCError();
        error.code = 701;
        error.message = "A normal error occured";
        const errorData = {
            context: { exception_class: "strange_error" },
        };
        error.exceptionName = "normal_error";
        error.data = errorData;
        function addDialog(dialogClass, props) {
            assert.strictEqual(dialogClass, NormalDialog);
            assert.deepEqual(props, {
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "A normal error occured",
                exceptionName: "normal_error",
                traceback: error.stack,
            });
        }
        serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
        await makeTestEnv();
        errorDialogRegistry.add("strange_error", CustomDialog);
        errorDialogRegistry.add("normal_error", NormalDialog);
        const errorEvent = new PromiseRejectionEvent("error", {
            reason: error,
            promise: null,
            cancelable: true,
        });
        await unhandledRejectionCb(errorEvent);
    }
);

QUnit.test("handle CONNECTION_LOST_ERROR", async (assert) => {
    patchWithCleanup(browser, {
        setTimeout: (callback, delay) => {
            assert.step(`set timeout (${delay === 2000 ? delay : ">2000"})`);
            callback();
        },
    });
    const mock = (message) => {
        assert.step(`create (${message})`);
        return () => {
            assert.step(`close`);
        };
    };
    serviceRegistry.add("notification", makeFakeNotificationService(mock), {
        force: true,
    });
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
    await makeTestEnv({ mockRPC });
    const error = new ConnectionLostError();
    const errorEvent = new PromiseRejectionEvent("error", {
        reason: error,
        promise: null,
        cancelable: true,
    });
    await unhandledRejectionCb(errorEvent);
    await nextTick(); // wait for mocked RPCs
    assert.verifySteps([
        "create (Connection lost. Trying to reconnect...)",
        "set timeout (2000)",
        "version_info",
        "set timeout (>2000)",
        "version_info",
        "close",
        "create (Connection restored. You are back online.)",
    ]);
});

QUnit.test("will let handlers from the registry handle errors first", async (assert) => {
    errorHandlerRegistry.add("__test_handler__", (env, err, originalError) => {
        assert.strictEqual(originalError, error);
        assert.strictEqual(env.someValue, 14);
        assert.step("in handler");
    });
    const testEnv = await makeTestEnv();
    testEnv.someValue = 14;
    const error = new Error();
    error.name = "boom";
    const errorEvent = new PromiseRejectionEvent("error", {
        reason: error,
        promise: null,
        cancelable: true,
    });
    await unhandledRejectionCb(errorEvent);
    assert.verifySteps(["in handler"]);
});

QUnit.test("originalError is the root cause of the error chain", async (assert) => {
    errorHandlerRegistry.add("__test_handler__", (env, err, originalError) => {
        assert.ok(err instanceof UncaughtPromiseError); // Wrapped by error service
        assert.ok(err.cause instanceof OwlError); // Wrapped by owl
        assert.strictEqual(err.cause.cause, originalError); // original error
        assert.step("in handler");
    });
    const testEnv = await makeTestEnv();
    testEnv.someValue = 14;
    const error = new Error();
    error.name = "boom";

    class ErrHandler extends Component {
        setup() {
            onError(async (err) => {
                await unhandledRejectionCb(
                    new PromiseRejectionEvent("error", {
                        reason: err,
                        promise: null,
                        cancelable: true,
                    })
                );
                prom.resolve();
            });
        }
    }
    ErrHandler.template = xml`<t t-component="props.comp"/>`;
    class ThrowInSetup extends Component {
        setup() {
            throw error;
        }
    }
    ThrowInSetup.template = xml``;
    let prom = makeDeferred();
    mount(ErrHandler, getFixture(), { props: { comp: ThrowInSetup } });
    await prom;
    assert.verifySteps(["in handler"]);

    class ThrowInWillStart extends Component {
        setup() {
            onWillStart(() => {
                throw error;
            });
        }
    }
    ThrowInWillStart.template = xml``;
    prom = makeDeferred();
    mount(ErrHandler, getFixture(), { props: { comp: ThrowInWillStart } });
    await prom;
    assert.verifySteps(["in handler"]);
});

QUnit.test("handle uncaught promise errors", async (assert) => {
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    function addDialog(dialogClass, props) {
        assert.strictEqual(dialogClass, ClientErrorDialog);
        assert.deepEqual(props, {
            name: "UncaughtPromiseError > TestError",
            message: "Uncaught Promise > This is an error test",
            traceback: error.stack,
        });
    }
    serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
    await makeTestEnv();

    const errorEvent = new PromiseRejectionEvent("error", {
        reason: error,
        promise: null,
        cancelable: true,
    });
    await unhandledRejectionCb(errorEvent);
});

QUnit.test("handle uncaught client errors", async (assert) => {
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    function addDialog(dialogClass, props) {
        assert.strictEqual(dialogClass, ClientErrorDialog);
        assert.strictEqual(props.name, "UncaughtClientError > TestError");
        assert.strictEqual(props.message, "Uncaught Javascript Error > This is an error test");
    }
    serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
    await makeTestEnv();

    const errorEvent = new ErrorEvent("error", {
        error,
        colno: 1,
        lineno: 1,
        filename: "test",
        cancelable: true,
    });
    await errorCb(errorEvent);
});

QUnit.test("handle uncaught CORS errors", async (assert) => {
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is a cors error";
    error.name = "CORS error";

    function addDialog(dialogClass, props) {
        assert.strictEqual(dialogClass, NetworkErrorDialog);
        assert.strictEqual(props.message, "Uncaught CORS Error");
    }
    serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
    await makeTestEnv();

    // CORS error event has no colno, no lineno and no filename
    const errorEvent = new ErrorEvent("error", { error, cancelable: true });
    await errorCb(errorEvent);
});

QUnit.test("check retry", async (assert) => {
    assert.expect(3);

    errorHandlerRegistry.add("__test_handler__", () => {
        assert.step("dispatched");
    });

    const def = makeDeferred();
    patchWithCleanup(browser, {
        setTimeout(fn) {
            def.then(fn);
        },
    });

    serviceRegistry.remove("dialog");
    await makeTestEnv();

    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    const errorEvent = new PromiseRejectionEvent("error", {
        reason: error,
        promise: null,
        cancelable: true,
    });
    await unhandledRejectionCb(errorEvent);

    assert.verifySteps([]);

    serviceRegistry.add("dialog", dialogService);
    await nextTick();

    await def.resolve();
    assert.verifySteps(["dispatched"]);
});

QUnit.test("lazy loaded handlers", async (assert) => {
    await makeTestEnv();
    const errorEvent = new PromiseRejectionEvent("error", {
        reason: new Error(),
        promise: null,
        cancelable: true,
    });

    await unhandledRejectionCb(errorEvent);
    assert.verifySteps([]);

    errorHandlerRegistry.add("__test_handler__", () => {
        assert.step("in handler");
    });

    await unhandledRejectionCb(errorEvent);
    assert.verifySteps(["in handler"]);
});

// The following test(s) do not want the preventDefault to be done automatically.
QUnit.module("Error Service", {
    beforeEach() {
        serviceRegistry.add("error", errorService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("rpc", makeFakeRPCService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        const windowAddEventListener = browser.addEventListener;
        browser.addEventListener = (type, cb) => {
            if (type === "unhandledrejection") {
                unhandledRejectionCb = cb;
            } else if (type === "error") {
                errorCb = cb;
            }
        };
        registerCleanup(() => {
            browser.addEventListener = windowAddEventListener;
        });
    },
});

QUnit.test("logs the traceback of the full error chain for unhandledrejection", async (assert) => {
    assert.expect(2);
    const regexParts = [
        /^.*This is a wrapper error/,
        /Caused by:.*This is a second wrapper error/,
        /Caused by:.*This is the original error/,
    ];
    const errorRegex = new RegExp(regexParts.map((re) => re.source).join(/[\s\S]*/.source));
    patchWithCleanup(console, {
        error(errorMessage) {
            assert.ok(errorRegex.test(errorMessage));
        },
    });

    const error = new Error("This is a wrapper error");
    error.cause = new Error("This is a second wrapper error");
    error.cause.cause = new Error("This is the original error");

    // start the services
    await makeTestEnv();
    const errorEvent = new PromiseRejectionEvent("unhandledrejection", {
        reason: error,
        promise: null,
        cancelable: true,
    });
    await unhandledRejectionCb(errorEvent);
    assert.ok(errorEvent.defaultPrevented);
});

QUnit.test("logs the traceback of the full error chain for uncaughterror", async (assert) => {
    assert.expect(2);
    const regexParts = [
        /^.*This is a wrapper error/,
        /Caused by:.*This is a second wrapper error/,
        /Caused by:.*This is the original error/,
    ];
    const errorRegex = new RegExp(regexParts.map((re) => re.source).join(/[\s\S]*/.source));
    patchWithCleanup(console, {
        error(errorMessage) {
            assert.ok(errorRegex.test(errorMessage));
        },
    });

    const error = new Error("This is a wrapper error");
    error.cause = new Error("This is a second wrapper error");
    error.cause.cause = new Error("This is the original error");

    // start the services
    await makeTestEnv();
    const errorEvent = new Event("error", {
        promise: null,
        cancelable: true,
    });
    errorEvent.error = error;
    errorEvent.filename = "dummy_file.js"; // needed to not be treated as a CORS error
    await errorCb(errorEvent);
    assert.ok(errorEvent.defaultPrevented);
});
