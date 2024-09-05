import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { Deferred, advanceTime, animationFrame } from "@odoo/hoot-mock";
import { Component, OwlError, onError, onWillStart, xml } from "@odoo/owl";
import {
    makeMockEnv,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import {
    ClientErrorDialog,
    RPCErrorDialog,
    standardErrorDialogProps,
} from "@web/core/errors/error_dialogs";
import { UncaughtPromiseError } from "@web/core/errors/error_service";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";

const errorDialogRegistry = registry.category("error_dialogs");
const errorHandlerRegistry = registry.category("error_handlers");

test("can handle rejected promise errors with a string as reason", async () => {
    expect.assertions(2);
    expect.errors(1);
    await makeMockEnv();
    errorHandlerRegistry.add(
        "__test_handler__",
        (env, err, originalError) => {
            expect(originalError).toBe("-- something went wrong --");
        },
        { sequence: 0 }
    );
    Promise.reject("-- something went wrong --");
    await animationFrame();
    expect.verifyErrors(["-- something went wrong --"]);
});

test("handle RPC_ERROR of type='server' and no associated dialog class", async () => {
    expect.assertions(5);
    expect.errors(1);
    const error = new RPCError();
    error.code = 701;
    error.message = "Some strange error occured";
    error.data = { debug: "somewhere" };
    error.subType = "strange_error";
    error.id = 12;
    error.model = "some model";

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(RPCErrorDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: {
                    debug: "somewhere",
                },
                subType: "strange_error",
                message: "Some strange error occured",
                exceptionName: null,
                id: 12,
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR/);
            expect(props.traceback).toMatch(/Some strange error occured/);
        },
    });
    await makeMockEnv();
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR: Some strange error occured"]);
});

test("handle custom RPC_ERROR of type='server' and associated custom dialog class", async () => {
    expect.assertions(5);
    expect.errors(1);
    class CustomDialog extends Component {
        static template = xml`<RPCErrorDialog title="'Strange Error'"/>`;
        static components = { RPCErrorDialog };
        static props = { ...standardErrorDialogProps };
    }
    const error = new RPCError();
    error.code = 701;
    error.message = "Some strange error occured";
    error.id = 12;
    error.model = "some model";
    const errorData = {
        context: { exception_class: "strange_error" },
        name: "strange_error",
    };
    error.data = errorData;

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(CustomDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "Some strange error occured",
                exceptionName: null,
                id: 12,
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR/);
            expect(props.traceback).toMatch(/Some strange error occured/);
        },
    });
    await makeMockEnv();
    errorDialogRegistry.add("strange_error", CustomDialog);
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR: Some strange error occured"]);
});

test("handle normal RPC_ERROR of type='server' and associated custom dialog class", async () => {
    expect.assertions(5);
    expect.errors(1);
    class CustomDialog extends Component {
        static template = xml`<RPCErrorDialog title="'Strange Error'"/>`;
        static components = { RPCErrorDialog };
        static props = ["*"];
    }
    class NormalDialog extends Component {
        static template = xml`<RPCErrorDialog title="'Normal Error'"/>`;
        static components = { RPCErrorDialog };
        static props = ["*"];
    }
    const error = new RPCError();
    error.code = 701;
    error.message = "A normal error occured";
    const errorData = {
        context: { exception_class: "strange_error" },
    };
    error.exceptionName = "normal_error";
    error.data = errorData;
    error.id = 12;
    error.model = "some model";
    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(NormalDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "A normal error occured",
                exceptionName: "normal_error",
                id: 12,
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR/);
            expect(props.traceback).toMatch(/A normal error occured/);
        },
    });
    await makeMockEnv();
    errorDialogRegistry.add("strange_error", CustomDialog);
    errorDialogRegistry.add("normal_error", NormalDialog);
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR: A normal error occured"]);
});

test("handle CONNECTION_LOST_ERROR", async () => {
    expect.errors(1);
    mockService("notification", {
        add(message) {
            expect.step(`create (${message})`);
            return () => {
                expect.step(`close`);
            };
        },
    });
    const values = [false, true]; // simulate the 'back online status' after 2 'version_info' calls
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        const online = values.shift();
        if (online) {
            return true;
        } else {
            return Promise.reject();
        }
    });

    await makeMockEnv();
    const error = new ConnectionLostError("/fake_url");
    Promise.reject(error);
    await animationFrame();
    patchWithCleanup(Math, {
        random: () => 0,
    });
    // wait for timeouts
    await advanceTime(2000);
    await advanceTime(3500);
    expect.verifySteps([
        "create (Connection lost. Trying to reconnect...)",
        "version_info",
        "version_info",
        "close",
        "create (Connection restored. You are back online.)",
    ]);
    expect.verifyErrors([
        `Error: Connection to "/fake_url" couldn't be established or was interrupted`,
    ]);
});

test("will let handlers from the registry handle errors first", async () => {
    expect.assertions(4);
    expect.errors(1);
    const testEnv = await makeMockEnv();
    testEnv.someValue = 14;
    errorHandlerRegistry.add("__test_handler__", (env, err, originalError) => {
        expect(originalError).toBe(error);
        expect(env.someValue).toBe(14);
        expect.step("in handler");
        return true;
    });
    const error = new Error();
    error.name = "boom";

    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["boom"]);
    expect.verifySteps(["in handler"]);
});

test("originalError is the root cause of the error chain", async () => {
    expect.assertions(10);
    expect.errors(2);
    await makeMockEnv();
    const error = new Error();
    error.name = "boom";
    errorHandlerRegistry.add("__test_handler__", (env, err, originalError) => {
        expect(err).toBeInstanceOf(UncaughtPromiseError); // Wrapped by error service
        expect(err.cause).toBeInstanceOf(OwlError); // Wrapped by owl
        expect(err.cause.cause).toBe(originalError); // original error
        expect.step("in handler");
        return true;
    });

    class ErrHandler extends Component {
        static template = xml`<t t-component="props.comp"/>`;
        static props = ["*"];
        setup() {
            onError(async (err) => {
                Promise.reject(err);
                await animationFrame();
                prom.resolve();
            });
        }
    }
    class ThrowInSetup extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            throw error;
        }
    }

    let prom = new Deferred();
    mountWithCleanup(ErrHandler, { props: { comp: ThrowInSetup } });
    await prom;
    expect.verifyErrors([
        `Error: An error occured in the owl lifecycle (see this Error's "cause" property)`,
    ]);
    expect.verifySteps(["in handler"]);

    class ThrowInWillStart extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            onWillStart(() => {
                throw error;
            });
        }
    }

    prom = new Deferred();
    mountWithCleanup(ErrHandler, { props: { comp: ThrowInWillStart } });
    await prom;
    expect.verifyErrors([`Error: The following error occurred in onWillStart: ""`]);
    expect.verifySteps(["in handler"]);
});

test("handle uncaught promise errors", async () => {
    expect.assertions(5);
    expect.errors(1);
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(ClientErrorDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "UncaughtPromiseError > TestError",
                message: "Uncaught Promise > This is an error test",
            });
            expect(props.traceback).toMatch(/TestError/);
            expect(props.traceback).toMatch(/This is an error test/);
        },
    });
    await makeMockEnv();

    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["TestError: This is an error test"]);
});

test("handle uncaught client errors", async () => {
    expect.assertions(4);
    expect.errors(1);
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(ClientErrorDialog);
            expect(props.name).toBe("UncaughtClientError > TestError");
            expect(props.message).toBe("Uncaught Javascript Error > This is an error test");
        },
    });
    await makeMockEnv();

    setTimeout(() => {
        throw error;
    });
    await animationFrame();
    expect.verifyErrors(["TestError: This is an error test"]);
});

test("don't show dialog for errors in third-party scripts", async () => {
    expect.errors(1);
    class TestError extends Error {}
    const error = new TestError();
    error.name = "Script error.";

    mockService("dialog", {
        add(_dialogClass, props) {
            throw new Error("should not pass here");
        },
    });
    await makeMockEnv();

    // Error events from errors in third-party scripts have no colno, no lineno and no filename
    // because of CORS.
    await manuallyDispatchProgrammaticEvent(window, "error", { error });
    await animationFrame();
    expect.verifyErrors(["Script error."]);
});

test("show dialog for errors in third-party scripts in debug mode", async () => {
    expect.errors(1);
    class TestError extends Error {}
    const error = new TestError();
    error.name = "Script error.";
    serverState.debug = true;

    mockService("dialog", {
        add(_dialogClass, props) {
            expect.step("Dialog: " + props.message);
            return () => {};
        },
    });
    await makeMockEnv();

    // Error events from errors in third-party scripts have no colno, no lineno and no filename
    // because of CORS.
    await manuallyDispatchProgrammaticEvent(window, "error", { error });
    await animationFrame();
    expect.verifyErrors(["Script error."]);
    expect.verifySteps(["Dialog: Third-Party Script Error"]);
});

test("lazy loaded handlers", async () => {
    expect.assertions(3);
    expect.errors(2);
    await makeMockEnv();

    Promise.reject(new Error("error"));
    await animationFrame();

    expect.verifyErrors(["Error: error"]);

    errorHandlerRegistry.add("__test_handler__", () => {
        expect.step("in handler");
        return true;
    });

    Promise.reject(new Error("error"));
    await animationFrame();

    expect.verifyErrors(["Error: error"]);
    expect.verifySteps(["in handler"]);
});

let unhandledRejectionCb;
let errorCb;

describe("Error Service Logs", () => {
    beforeEach(() => {
        patchWithCleanup(browser, {
            addEventListener: (type, cb) => {
                if (type === "unhandledrejection") {
                    unhandledRejectionCb = cb;
                } else if (type === "error") {
                    errorCb = cb;
                }
            },
        });
    });

    test("logs the traceback of the full error chain for unhandledrejection", async () => {
        expect.assertions(2);
        const regexParts = [
            /^.*This is a wrapper error/,
            /Caused by:.*This is a second wrapper error/,
            /Caused by:.*This is the original error/,
        ];
        const errorRegex = new RegExp(regexParts.map((re) => re.source).join(/[\s\S]*/.source));
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(errorRegex);
            },
        });

        const error = new Error("This is a wrapper error");
        error.cause = new Error("This is a second wrapper error");
        error.cause.cause = new Error("This is the original error");

        await makeMockEnv();
        const errorEvent = new PromiseRejectionEvent("unhandledrejection", {
            reason: error,
            promise: null,
            cancelable: true,
        });
        await unhandledRejectionCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
    });

    test("logs the traceback of the full error chain for uncaughterror", async () => {
        expect.assertions(2);
        const regexParts = [
            /^.*This is a wrapper error/,
            /Caused by:.*This is a second wrapper error/,
            /Caused by:.*This is the original error/,
        ];
        const errorRegex = new RegExp(regexParts.map((re) => re.source).join(/[\s\S]*/.source));
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(errorRegex);
            },
        });

        const error = new Error("This is a wrapper error");
        error.cause = new Error("This is a second wrapper error");
        error.cause.cause = new Error("This is the original error");

        await makeMockEnv();
        const errorEvent = new Event("error", {
            promise: null,
            cancelable: true,
        });
        errorEvent.error = error;
        errorEvent.filename = "dummy_file.js"; // needed to not be treated as a CORS error
        await errorCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
    });
});
