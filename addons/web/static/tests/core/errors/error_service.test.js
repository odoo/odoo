// @ts-check

import { beforeEach, describe, expect, mockSendBeacon, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, onError, onWillStart, OwlError, xml } from "@odoo/owl";
import {
    makeMockEnv,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import {
    ClientErrorDialog,
    RPCErrorDialog,
    SessionExpiredDialog,
    standardErrorDialogProps,
    WarningDialog,
} from "@web/components/errors/error_dialogs";
import {
    defaultHandler,
    supersededErrorHandler,
} from "@web/components/errors/error_handlers";
import { browser } from "@web/core/browser/browser";
import { UncaughtPromiseError } from "@web/core/errors/error_service";
import {
    ConnectionLostError,
    makeErrorFromResponse,
    RPCError,
} from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { omit } from "@web/core/utils/collections/objects";
import { SupersededError } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { swallowAllVisitorErrors } from "@web/webclient/errors/visitor_error_handler";

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
        { sequence: 0 },
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
    error.model = "some model";

    mockService("dialog", {
        add(dialogClass, /** @type {any} */ props) {
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
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR/);
            expect(props.traceback).toMatch(/Some strange error occured/);
            return async () => {};
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
    error.model = "some model";
    const errorData = {
        context: { exception_class: "strange_error" },
        name: "strange_error",
    };
    error.data = errorData;

    mockService("dialog", {
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(CustomDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "Some strange error occured",
                exceptionName: null,
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR/);
            expect(props.traceback).toMatch(/Some strange error occured/);
            return async () => {};
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
    error.model = "some model";
    mockService("dialog", {
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(NormalDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "RPC_ERROR",
                type: "server",
                code: 701,
                data: errorData,
                subType: null,
                message: "A normal error occured",
                exceptionName: "normal_error",
                model: "some model",
            });
            expect(props.traceback).toMatch(/RPC_ERROR/);
            expect(props.traceback).toMatch(/A normal error occured/);
            return async () => {};
        },
    });
    await makeMockEnv();
    errorDialogRegistry.add("strange_error", CustomDialog);
    errorDialogRegistry.add("normal_error", NormalDialog);
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR: A normal error occured"]);
});

test("session-expired RPC error (code 100) routes to SessionExpiredDialog", async () => {
    expect.assertions(3);
    expect.errors(1);
    const error = makeErrorFromResponse({
        code: 100,
        message: "Odoo Session Expired",
        data: {
            name: "odoo.http.SessionExpiredException",
            message: "Session expired",
            arguments: [],
            context: {},
            debug: "",
        },
    });
    mockService("dialog", {
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(SessionExpiredDialog);
            expect(props.exceptionName).toBe("odoo.http.SessionExpiredException");
            return async () => {};
        },
    });
    await makeMockEnv();
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR: Odoo Session Expired"]);
});

test("ServerActionWithWarningsError routes to WarningDialog", async () => {
    expect.errors(1);
    mockService("dialog", {
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(WarningDialog);
            expect.step(props.exceptionName);
            return async () => {};
        },
    });
    await makeMockEnv();
    const serializedNames = [
        "odoo.addons.base.models.ir_actions_server.ServerActionWithWarningsError",
    ];
    for (const name of serializedNames) {
        const error = makeErrorFromResponse({
            code: 200,
            message: "Odoo Server Error",
            data: {
                name,
                message: "The server action has warnings",
                arguments: ["The server action has warnings"],
                context: {},
                debug: "",
            },
        });
        Promise.reject(error);
        await animationFrame();
    }
    expect.verifyErrors(["RPC_ERROR: Odoo Server Error"]);
    expect.verifySteps(serializedNames);
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
    const values = [false, true];
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
        `ConnectionLostError: Connection to "/fake_url" couldn't be established or was interrupted`,
    ]);
});

test("defaultHandler tolerates an error event target without a location", async () => {
    const env = {
        services: {
            dialog: {
                add(/** @type {any} */ _DialogComponent, /** @type {any} */ props) {
                    expect.step("dialog");
                    expect(props.serverHost).toBe(undefined);
                },
            },
        },
    };
    const error = new Error("boom");
    /** @type {any} */ (error).event = { target: {} };

    defaultHandler(/** @type {any} */ (env), /** @type {any} */ (error));
    expect.verifySteps(["dialog"]);
});

test("CONNECTION_LOST_ERROR reconnection backoff is capped at 60s", async () => {
    expect.errors(1);
    let online = false;
    let versionInfoCalls = 0;
    mockService("notification", {
        add() {
            return async () => {};
        },
    });
    onRpc("/web/webclient/version_info", async () => {
        versionInfoCalls++;
        return online ? true : Promise.reject();
    });
    patchWithCleanup(Math, {
        random: () => 0,
    });

    await makeMockEnv();
    Promise.reject(new ConnectionLostError("/fake_url"));
    await animationFrame();

    for (let i = 0; i < 80; i++) {
        await advanceTime(60_000);
    }
    expect(versionInfoCalls > 30).toBe(true);

    online = true;
    await advanceTime(60_000);

    expect.verifyErrors([
        `ConnectionLostError: Connection to "/fake_url" couldn't be established or was interrupted`,
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
        expect(err).toBeInstanceOf(UncaughtPromiseError);
        expect(err.cause).toBeInstanceOf(OwlError);
        expect(err.cause.cause).toBe(originalError);
        expect.step("in handler");
        return true;
    });

    class ErrHandler extends Component {
        static template = xml`<t t-component="this.props.comp"/>`;
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
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(ClientErrorDialog);
            expect(omit(props, "traceback", "serverHost")).toEqual({
                name: "UncaughtPromiseError > TestError",
                message: "Uncaught Promise > This is an error test",
            });
            expect(props.traceback).toMatch(/TestError/);
            expect(props.traceback).toMatch(/This is an error test/);
            return async () => {};
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
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(ClientErrorDialog);
            expect(props.name).toBe("UncaughtClientError > TestError");
            expect(props.message).toBe(
                "Uncaught Javascript Error > This is an error test",
            );
            return async () => {};
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

    await manuallyDispatchProgrammaticEvent(window, "error", { error });
    await animationFrame();
    expect.verifyErrors(["Script error."]);
});

test("show dialog for errors in third-party scripts in debug mode", async () => {
    expect.errors(1);
    class TestError extends Error {}
    const error = new TestError();
    error.name = "Script error.";
    serverState.debug = "1";

    mockService("dialog", {
        add(_dialogClass, props) {
            expect.step("Dialog: " + props.message);
            return async () => {};
        },
    });
    await makeMockEnv();

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

test("supersededErrorHandler runs before the dialog handlers", async () => {
    const env = await makeMockEnv();
    const names = errorHandlerRegistry.getEntries().map(([name]) => name);
    expect(names.indexOf("supersededErrorHandler")).toBeLessThan(
        names.indexOf("defaultHandler"),
    );

    let prevented = false;
    const uncaught = new UncaughtPromiseError();
    /** @type {any} */ (uncaught).event = { preventDefault: () => (prevented = true) };
    expect(supersededErrorHandler(env, uncaught, new SupersededError())).toBe(true);
    expect(prevented).toBe(true);
    expect(supersededErrorHandler(env, uncaught, new Error("real"))).toBe(false);
});

/** @type {any} */
let unhandledRejectionCb;
/** @type {any} */
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
        const errorRegex = new RegExp(
            regexParts.map((re) => re.source).join(/[\s\S]*/.source),
        );
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(errorRegex);
            },
        });

        const error = new Error("This is a wrapper error", {
            cause: new Error("This is a second wrapper error", {
                cause: new Error("This is the original error"),
            }),
        });

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
        const errorRegex = new RegExp(
            regexParts.map((re) => re.source).join(/[\s\S]*/.source),
        );
        patchWithCleanup(console, {
            error(errorMessage) {
                expect(errorMessage).toMatch(errorRegex);
            },
        });

        const error = new Error("This is a wrapper error", {
            cause: new Error("This is a second wrapper error", {
                cause: new Error("This is the original error"),
            }),
        });

        await makeMockEnv();
        const errorEvent = new ErrorEvent("error", {
            cancelable: true,
            error,
            filename: "dummy_file.js",
        });
        await errorCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
    });

    test("a genuine defect is beaconed to js_error", async () => {
        const beacons = [];
        mockSendBeacon((url, blob) => {
            beacons.push({ url, blob });
            return true;
        });
        patchWithCleanup(console, { error() {} });
        await makeMockEnv();
        const errorEvent = new ErrorEvent("error", {
            cancelable: true,
            error: new Error("a real defect"),
            filename: "foo.js",
            lineno: 7,
            colno: 3,
        });
        await errorCb(errorEvent);
        expect(beacons).toHaveLength(1);
        expect(beacons[0].url).toBe("/web/observability/js_error");
        const payload = JSON.parse(await beacons[0].blob.text());
        expect(payload.kind).toBe("error");
        expect(payload.message).toBe("a real defect");
    });

    test("a handled business error is not beaconed", async () => {
        const beacons = [];
        mockSendBeacon((url, blob) => {
            beacons.push({ url, blob });
            return true;
        });
        await makeMockEnv();
        const errorEvent = new PromiseRejectionEvent("unhandledrejection", {
            reason: new SupersededError(),
            promise: null,
            cancelable: true,
        });
        await unhandledRejectionCb(errorEvent);
        expect(beacons).toHaveLength(0);
    });

    test("a visitor's swallowed defect is still beaconed (dialog hidden, defect observable)", async () => {
        patchWithCleanup(user, { isInternalUser: false });
        patchWithCleanup(session, { test_mode: false });
        errorHandlerRegistry.add("swallowAllVisitorErrors", swallowAllVisitorErrors, {
            sequence: 0,
        });
        const beacons = [];
        mockSendBeacon((url, blob) => {
            beacons.push({ url, blob });
            return true;
        });
        let dialogShown = false;
        mockService("dialog", {
            add() {
                dialogShown = true;
                return async () => {};
            },
        });
        patchWithCleanup(console, { error() {} });
        await makeMockEnv();

        const errorEvent = new ErrorEvent("error", {
            cancelable: true,
            error: new Error("public page defect"),
            filename: "foo.js",
        });
        await errorCb(errorEvent);

        expect(dialogShown).toBe(false);
        expect(beacons).toHaveLength(1);
        expect(errorEvent.defaultPrevented).toBe(true);
        const payload = JSON.parse(await beacons[0].blob.text());
        expect(payload.message).toBe("public page defect");
    });

    test("error in handlers while handling an error", async () => {
        errorHandlerRegistry.add(
            "__test_handler__",
            (env, err, originalError) => {
                throw new Error("Boom in handler");
            },
            { sequence: 0 },
        );
        let sawLaterHandler = false;
        errorHandlerRegistry.add(
            "__later_handler__",
            () => {
                sawLaterHandler = true;
            },
            { sequence: 1 },
        );
        patchWithCleanup(console, {
            error(errorMessage) {
                const msg = String(errorMessage);
                if (
                    msg.startsWith(
                        '@web/core/errors/error_service: handler "__test_handler__"',
                    )
                ) {
                    expect(msg).toMatch(
                        /failed with "Error: Boom in handler" while trying to handle:\nError: Genuine Business Boom/,
                    );
                    expect.step("handler crash logged");
                } else if (msg.includes("Genuine Business Boom")) {
                    expect.step("traceback logged");
                }
            },
        });

        await makeMockEnv();
        /** @type {ErrorEvent | PromiseRejectionEvent} */
        let errorEvent = new ErrorEvent("error", {
            cancelable: true,
            error: Object.assign(new Error("Genuine Business Boom"), {
                annotatedTraceback: "annotated",
            }),
            filename: "dummy_file.js",
        });
        await errorCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
        expect(sawLaterHandler).toBe(true);
        expect.verifySteps(["handler crash logged", "traceback logged"]);

        sawLaterHandler = false;
        errorEvent = new PromiseRejectionEvent("unhandledrejection", {
            promise: null,
            cancelable: true,
            reason: new Error("Genuine Business Boom"),
        });
        await unhandledRejectionCb(errorEvent);
        expect(errorEvent.defaultPrevented).toBe(true);
        expect(sawLaterHandler).toBe(true);
        expect.verifySteps(["handler crash logged", "traceback logged"]);
    });
});

test("a 403 Forbidden routes to WarningDialog, not the session-expired dialog", async () => {
    expect.assertions(4);
    expect.errors(1);
    const error = makeErrorFromResponse({
        code: 200,
        message: "Odoo Server Error",
        data: {
            name: "werkzeug.exceptions.Forbidden",
            message: "You are not allowed to do that",
            arguments: [],
            context: {},
            debug: "",
        },
    });
    mockService("dialog", {
        add(dialogClass, /** @type {any} */ props) {
            expect(dialogClass).toBe(WarningDialog);
            expect(dialogClass).not.toBe(SessionExpiredDialog);
            expect(props.exceptionName).toBe("werkzeug.exceptions.Forbidden");
            return async () => {};
        },
    });
    await makeMockEnv();
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR: Odoo Server Error"]);
});

describe("the reported class depends on the debug mode", () => {
    /**
     * @param {string} debug
     * @returns {Promise<string[]>}
     */
    async function reportedFor(debug) {
        /** @type {string[]} */
        const seen = [];
        registry.category("error_handlers").add(
            "class_probe",
            (_env, uncaught) => {
                seen.push(uncaught.constructor.name);
                return true;
            },
            { sequence: 1 },
        );
        const env = await makeMockEnv();
        patchWithCleanup(env, { debug });
        const service = registry.category("services").get("error").start(env, {});
        const error = new Error("boom");
        await service
            .onError({
                error,
                filename: "/a.js",
                lineno: 1,
                colno: 1,
                message: "boom",
                type: "error",
                defaultPrevented: false,
                preventDefault() {},
            })
            .catch((e) => seen.push(e === error ? "RETHROWN" : `THREW:${e}`));
        service.destroy();
        return seen;
    }

    test("without debug=assets the handlers see an UncaughtClientError", async () => {
        expect(await reportedFor("1")).toEqual(["UncaughtClientError"]);
    });

    test("with debug=assets onError re-throws instead, and reports on re-entry", async () => {
        expect(await reportedFor("assets")).toEqual(["RETHROWN"]);
    });
});
