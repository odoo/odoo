import { browser } from "@web/core/browser/browser";
import { describe, test, expect } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-mock";
import {
    mountWithCleanup,
    patchWithCleanup,
    mockService,
    makeDialogMockEnv,
} from "@web/../tests/web_test_helpers";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import {
    ClientErrorDialog,
    Error504Dialog,
    ErrorDialog,
    RedirectWarningDialog,
    SessionExpiredDialog,
    WarningDialog,
} from "@web/core/errors/error_dialogs";

describe.current.tags("desktop");

test("ErrorDialog with traceback", async () => {
    expect(".o_dialog").toHaveCount(0);
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ErrorDialog, {
        env,
        props: {
            message: "Something bad happened",
            data: { debug: "Some strange unreadable stack" },
            name: "ERROR_NAME",
            traceback: "This is a traceback string",
            close() {},
        },
    });
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Odoo Error");
    expect("main button").toHaveText("See details");
    expect(queryAllTexts("footer button")).toEqual(["Close", "Copy error to clipboard"]);
    expect(queryAllTexts("main p > p")).toEqual([
        "An error occurred",
        "Please use the copy button to report the error to your support service.",
    ]);
    expect("div.o_error_detail").toHaveCount(0);
    click("main button");
    await animationFrame();
    expect("main .clearfix p").toHaveText("Something bad happened");
    expect("main .clearfix code").toHaveText("ERROR_NAME");
    expect("div.o_error_detail").toHaveCount(1);
    expect("div.o_error_detail").toHaveText("This is a traceback string");
});

test("Client ErrorDialog with traceback", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ClientErrorDialog, {
        env,
        props: {
            message: "Something bad happened",
            data: { debug: "Some strange unreadable stack" },
            name: "ERROR_NAME",
            traceback: "This is a traceback string",
            close() {},
        },
    });
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Odoo Client Error");
    expect("main button").toHaveText("See details");
    expect(queryAllTexts("footer button")).toEqual(["Close", "Copy error to clipboard"]);
    expect(queryAllTexts("main p > p")).toEqual([
        "An error occurred",
        "Please use the copy button to report the error to your support service.",
    ]);
    expect("div.o_error_detail").toHaveCount(0);
    click("main button");
    await animationFrame();
    expect("main .clearfix p").toHaveText("Something bad happened");
    expect("main .clearfix code").toHaveText("ERROR_NAME");
    expect("div.o_error_detail").toHaveCount(1);
    expect("div.o_error_detail").toHaveText("This is a traceback string");
});

test("button clipboard copy error traceback", async () => {
    expect.assertions(1);
    const error = new Error();
    error.name = "ERROR_NAME";
    error.message = "This is the message";
    error.traceback = "This is a traceback";
    patchWithCleanup(navigator.clipboard, {
        writeText(value) {
            expect(value).toBe(`${error.name}\n${error.message}\n${error.traceback}`);
        },
    });
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ErrorDialog, {
        env,
        props: {
            message: error.message,
            name: error.name,
            traceback: error.traceback,
            close() {},
        },
    });
    click(".fa-clipboard");
    await tick();
});

test("WarningDialog", async () => {
    expect(".o_dialog").toHaveCount(0);
    const env = await makeDialogMockEnv();
    await mountWithCleanup(WarningDialog, {
        env,
        props: {
            exceptionName: "odoo.exceptions.UserError",
            message: "...",
            data: { arguments: ["Some strange unreadable message"] },
            close() {},
        },
    });
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Invalid Operation");
    expect(".o_error_dialog").toHaveCount(1);
    expect("main").toHaveText("Some strange unreadable message");
    expect(".o_dialog footer button").toHaveText("Close");
});

test("RedirectWarningDialog", async () => {
    mockService("action", {
        doAction(actionId) {
            expect.step(actionId);
        },
    });
    expect(".o_dialog").toHaveCount(0);
    const env = await makeDialogMockEnv();
    await mountWithCleanup(RedirectWarningDialog, {
        env,
        props: {
            data: {
                arguments: [
                    "Some strange unreadable message",
                    "buy_action_id",
                    "Buy book on cryptography",
                ],
            },
            close() {
                expect.step("dialog-closed");
            },
        },
    });
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Odoo Warning");
    expect("main").toHaveText("Some strange unreadable message");
    expect(queryAllTexts("footer button")).toEqual(["Buy book on cryptography", "Close"]);

    click("footer button:nth-child(1)"); // click on "Buy book on cryptography"
    await animationFrame();
    expect(["buy_action_id", "dialog-closed"]).toVerifySteps();

    click("footer button:nth-child(2)"); // click on "Cancel"
    await animationFrame();
    expect(["dialog-closed"]).toVerifySteps();
});

test("Error504Dialog", async () => {
    expect(".o_dialog").toHaveCount(0);
    const env = await makeDialogMockEnv();
    await mountWithCleanup(Error504Dialog, { env, props: { close() {} } });
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Request timeout");
    expect("main p").toHaveText(
        "The operation was interrupted. This usually means that the current operation is taking too much time."
    );
    expect(".o_dialog footer button").toHaveText("Close");
});

test("SessionExpiredDialog", async () => {
    patchWithCleanup(browser.location, {
        reload() {
            expect.step("location reload");
        },
    });
    expect(".o_dialog").toHaveCount(0);
    const env = await makeDialogMockEnv();
    await mountWithCleanup(SessionExpiredDialog, { env, props: { close() {} } });
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Odoo Session Expired");
    expect("main p").toHaveText(
        "Your Odoo session expired. The current page is about to be refreshed."
    );
    expect(".o_dialog footer button").toHaveText("Close");
    click(".o_dialog footer button");
    await animationFrame();
    expect(["location reload"]).toVerifySteps();
});
