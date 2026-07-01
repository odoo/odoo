import {
    animationFrame,
    beforeEach,
    describe,
    expect,
    manuallyDispatchProgrammaticEvent,
    test,
} from "@odoo/hoot";
import { Component, onWillStart, props, xml } from "@odoo/owl";
import {
    makeMockEnv,
    mockService,
    mountWithCleanup,
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
import { RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const errorDialogRegistry = registry.category("error_dialogs");
const errorHandlerRegistry = registry.category("error_handlers");

test("can handle rejected promise errors with a string as reason", async () => {
    await makeMockEnv();
    errorHandlerRegistry.add(
        "__test_handler__",
        (env, err, originalError) => {
            expect.step(originalError);
        },
        { sequence: 0 }
    );

    expect.errors(1);
    Promise.reject("-- something went wrong --");

    await expect.waitForSteps(["-- something went wrong --"]);
    expect.verifyErrors(["-- something went wrong --"]);
});

test("handle RPC_ERROR of type='server' and no associated dialog class", async () => {
    const error = new RPCError();
    error.code = 701;
    error.message = "Some strange error occurred";
    error.data = { debug: "somewhere" };
    error.subType = "strange_error";
    error.model = "some model";

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(RPCErrorDialog);
            expect(props).toMatchObject({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: {
                    debug: "somewhere",
                },
                subType: "strange_error",
                message: "Some strange error occurred",
                exceptionName: null,
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR: Some strange error occurred/);
            expect.step("dialog.add");
        },
    });
    await makeMockEnv();

    expect.errors(1);
    Promise.reject(error);

    await expect.waitForSteps(["dialog.add"]);
    expect.verifyErrors(["RPC_ERROR: Some strange error occurred"]);
});

test("handle custom RPC_ERROR of type='server' and associated custom dialog class", async () => {
    class CustomDialog extends Component {
        static template = xml`<RPCErrorDialog title="'Strange Error'"/>`;
        static components = { RPCErrorDialog };
        static props = { ...standardErrorDialogProps };
    }
    const error = new RPCError();
    error.code = 701;
    error.message = "Some strange error occurred";
    error.model = "some model";
    const errorData = {
        context: { exception_class: "strange_error" },
        name: "strange_error",
    };
    error.data = errorData;

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(CustomDialog);
            expect(props).toMatchObject({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "Some strange error occurred",
                exceptionName: null,
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR: Some strange error occurred/);
            expect.step("dialog.add");
        },
    });
    await makeMockEnv();
    errorDialogRegistry.add("strange_error", CustomDialog);

    expect.errors(1);
    Promise.reject(error);

    await expect.waitForSteps(["dialog.add"]);
    expect.verifyErrors(["RPC_ERROR: Some strange error occurred"]);
});

test("handle normal RPC_ERROR of type='server' and associated custom dialog class", async () => {
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
    error.message = "A normal error occurred";
    const errorData = {
        context: { exception_class: "strange_error" },
    };
    error.exceptionName = "normal_error";
    error.data = errorData;
    error.model = "some model";
    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(NormalDialog);
            expect(props).toMatchObject({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "A normal error occurred",
                exceptionName: "normal_error",
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR: A normal error occurred/);
            expect.step("dialog.add");
        },
    });
    await makeMockEnv();
    errorDialogRegistry.add("strange_error", CustomDialog);
    errorDialogRegistry.add("normal_error", NormalDialog);

    expect.errors(1);
    Promise.reject(error);

    await expect.waitForSteps(["dialog.add"]);
    expect.verifyErrors(["RPC_ERROR: A normal error occurred"]);
});

test("will let handlers from the registry handle errors first", async () => {
    await makeMockEnv({ someValue: 14 });
    errorHandlerRegistry.add("__test_handler__", (env, err, originalError) => {
        expect(originalError).toBe(error);
        expect(env.someValue).toBe(14);
        expect.step("in handler");
        return true;
    });
    const error = new Error();
    error.name = "boom";

    expect.errors(1);
    Promise.reject(error);

    await expect.waitForSteps(["in handler"]);
    expect.verifyErrors(["boom"]);
});

test("originalError is the root cause of the error chain", async () => {
    errorHandlerRegistry.add("__test_handler__", (env, err, originalError) => {
        expect(err).toBeInstanceOf(UncaughtPromiseError); // Wrapped by error service
        // owl no longer wraps lifecycle errors in OwlError, so the cause is the original error directly
        expect(err.cause).toBe(originalError);
        expect.step("in handler");
        return true;
    });

    class ErrHandler extends Component {
        static template = xml`<t t-component="this.props.comp"/>`;

        props = props();
    }

    const error1 = new Error();
    error1.name = "boom";
    class ThrowInSetup extends Component {
        static template = xml``;
        setup() {
            throw error1;
        }
    }

    expect.errors(2);
    mountWithCleanup(ErrHandler, { props: { comp: ThrowInSetup } });
    await expect.waitForSteps(["in handler"]);
    expect.verifyErrors(["boom"]);

    const error2 = new Error();
    error2.name = "boom";
    class ThrowInWillStart extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            onWillStart(() => {
                throw error2;
            });
        }
    }

    mountWithCleanup(ErrHandler, { props: { comp: ThrowInWillStart } });
    await expect.waitForSteps(["in handler"]);
    expect.verifyErrors(["boom"]);
});

test("handle uncaught promise errors", async () => {
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(ClientErrorDialog);
            expect(props).toMatchObject({
                name: "UncaughtPromiseError > TestError",
                message: "Uncaught Promise > This is an error test",
            });
            expect(props.traceback).toMatch(/TestError: This is an error test/);
            expect.step("dialog.add");
        },
    });
    await makeMockEnv();

    expect.errors(1);
    Promise.reject(error);

    await expect.waitForSteps(["dialog.add"]);
    expect.verifyErrors(["TestError: This is an error test"]);
});

test("handle uncaught client errors", async () => {
    class TestError extends Error {}
    const error = new TestError();
    error.message = "This is an error test";
    error.name = "TestError";

    mockService("dialog", {
        add(dialogClass, props) {
            expect(dialogClass).toBe(ClientErrorDialog);
            expect(props.name).toBe("UncaughtClientError > TestError");
            expect(props.message).toBe("Uncaught Javascript Error > This is an error test");
            expect.step("dialog.add");
        },
    });
    await makeMockEnv();

    expect.errors(1);
    setTimeout(() => {
        throw error;
    });

    await expect.waitForSteps(["dialog.add"]);
    expect.verifyErrors(["TestError: This is an error test"]);
});

test("don't show dialog for errors in third-party scripts", async () => {
    class TestError extends Error {}
    const error = new TestError();
    error.name = "Script error.";

    mockService("dialog", {
        add(_dialogClass, props) {
            throw new Error("should not pass here");
        },
    });
    await makeMockEnv();

    expect.errors(1);
    // Error events from errors in third-party scripts have no colno, no lineno and no filename
    // because of CORS.
    await manuallyDispatchProgrammaticEvent(window, "error", { error });

    await expect.waitForErrors(["Script error."]);
});

test("show dialog for errors in third-party scripts in debug mode", async () => {
    class TestError extends Error {}
    const error = new TestError();
    error.name = "Script error.";
    serverState.debug = "1";

    mockService("dialog", {
        add(_dialogClass, props) {
            expect.step("Dialog: " + props.message);
            return () => {};
        },
    });
    await makeMockEnv();

    expect.errors(1);
    // Error events from errors in third-party scripts have no colno, no lineno and no filename
    // because of CORS.
    await manuallyDispatchProgrammaticEvent(window, "error", { error });
    await expect.waitForSteps(["Dialog: Third-Party Script Error"]);
    expect.verifyErrors(["Script error."]);
});

test("lazy loaded handlers", async () => {
    await makeMockEnv();

    expect.errors(2);
    Promise.reject(new Error("error"));
    await animationFrame();

    await expect.waitForErrors(["Error: error"]);

    errorHandlerRegistry.add("__test_handler__", () => {
        expect.step("in handler");
        return true;
    });

    Promise.reject(new Error("error"));

    await expect.waitForSteps(["in handler"]);
    expect.verifyErrors(["Error: error"]);
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
        const regexParts = [
            /^.*This is a wrapper error/,
            /Caused by:.*This is a second wrapper error/,
            /Caused by:.*This is the original error/,
        ];
        const errorRegex = new RegExp(regexParts.map((re) => re.source).join(/[\s\S]*/.source));
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(errorRegex);
                expect.step("console.error");
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
        expect.verifySteps(["console.error"]);
        expect(errorEvent.defaultPrevented).toBe(true);
    });

    test("logs the traceback of the full error chain for uncaughterror", async () => {
        const regexParts = [
            /^.*This is a wrapper error/,
            /Caused by:.*This is a second wrapper error/,
            /Caused by:.*This is the original error/,
        ];
        const errorRegex = new RegExp(regexParts.map((re) => re.source).join(/[\s\S]*/.source));
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(errorRegex);
                expect.step("console.error");
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
        expect.verifySteps(["console.error"]);
        expect(errorEvent.defaultPrevented).toBe(true);
    });

    test("error in handlers while handling an error", async () => {
        // Scenario: an error occurs at the early stage of the "boot" sequence, error handlers
        // that are supposed to spawn dialogs are not ready then and will crash.
        // We assert that *exactly one* error message is logged, that contains the original error's traceback
        // and an indication that a handler has crashed just for not loosing information.
        // The crash of the error handler should merely be seen as a consequence of the early stage at which the error occurs.
        errorHandlerRegistry.add(
            "__test_handler__",
            (env, err, originalError) => {
                throw new Error("Boom in handler");
            },
            { sequence: 0 }
        );
        // We want to assert that the error_service code does the preventDefault.
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(
                    /^@web\/core\/error_service: handler "__test_handler__" failed with "Error: Boom in handler" while trying to handle:\nError: Genuine Business Boom.*/
                );
                expect.step("error logged");
            },
        });

        await makeMockEnv();
        let errorEvent = new Event("error", {
            promise: null,
            cancelable: true,
        });

        errorEvent.error = new Error("Genuine Business Boom");
        errorEvent.error.annotatedTraceback = "annotated";
        errorEvent.filename = "dummy_file.js"; // needed to not be treated as a CORS error
        await errorCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
        expect.verifySteps(["error logged"]);

        errorEvent = new PromiseRejectionEvent("unhandledrejection", {
            promise: null,
            cancelable: true,
            reason: new Error("Genuine Business Boom"),
        });
        await unhandledRejectionCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
        expect.verifySteps(["error logged"]);
    });
});
