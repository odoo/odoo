/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import {
    ClientErrorDialog,
    Error504Dialog,
    ErrorDialog,
    RedirectWarningDialog,
    SessionExpiredDialog,
    WarningDialog,
} from "@web/core/errors/error_dialogs";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeDialogService, makeFakeLocalizationService } from "../../helpers/mock_services";
import { click, getFixture, mount, nextTick, patchWithCleanup } from "../../helpers/utils";

let target;
let env;
const serviceRegistry = registry.category("services");

async function makeDialogTestEnv() {
    const env = await makeTestEnv();
    env.dialogData = {
        isActive: true,
        close() {},
    };
    return env;
}

QUnit.module("Error dialogs", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("dialog", makeFakeDialogService());
    },
});

QUnit.test("ErrorDialog with traceback", async (assert) => {
    assert.expect(11);
    assert.containsNone(target, ".o_dialog");
    env = await makeDialogTestEnv();
    await mount(ErrorDialog, target, {
        env,
        props: {
            message: "Something bad happened",
            data: { debug: "Some strange unreadable stack" },
            name: "ERROR_NAME",
            traceback: "This is a tracback string",
            close() {},
        },
    });
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Odoo Error");
    const mainButtons = target.querySelectorAll("main button");
    assert.deepEqual(
        [...mainButtons].map((el) => el.textContent),
        ["Copy the full error to clipboard", "See details"]
    );
    assert.deepEqual(
        [...target.querySelectorAll("main .clearfix p")].map((el) => el.textContent),
        [
            "An error occurred",
            "Please use the copy button to report the error to your support service.",
        ]
    );
    assert.containsNone(target, "div.o_error_detail");
    assert.strictEqual(target.querySelector(".o_dialog footer button").textContent, "Ok");
    click(mainButtons[1]);
    await nextTick();
    assert.deepEqual(
        [...target.querySelectorAll("main .clearfix p")].map((el) => el.textContent),
        [
            "An error occurred",
            "Please use the copy button to report the error to your support service.",
            "Something bad happened",
        ]
    );
    assert.deepEqual(
        [...target.querySelectorAll("main .clearfix code")].map((el) => el.textContent),
        ["ERROR_NAME"]
    );
    assert.containsOnce(target, "div.o_error_detail");
    assert.strictEqual(
        target.querySelector("div.o_error_detail").textContent,
        "This is a tracback string"
    );
});

QUnit.test("Client ErrorDialog with traceback", async (assert) => {
    assert.expect(11);
    assert.containsNone(target, ".o_dialog");
    env = await makeDialogTestEnv();
    await mount(ClientErrorDialog, target, {
        env,
        props: {
            message: "Something bad happened",
            data: { debug: "Some strange unreadable stack" },
            name: "ERROR_NAME",
            traceback: "This is a traceback string",
            close() {},
        },
    });
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(
        target.querySelector("header .modal-title").textContent,
        "Odoo Client Error"
    );
    const mainButtons = target.querySelectorAll("main button");
    assert.deepEqual(
        [...mainButtons].map((el) => el.textContent),
        ["Copy the full error to clipboard", "See details"]
    );
    assert.deepEqual(
        [...target.querySelectorAll("main .clearfix p")].map((el) => el.textContent),
        [
            "An error occurred",
            "Please use the copy button to report the error to your support service.",
        ]
    );
    assert.containsNone(target, "div.o_error_detail");
    assert.strictEqual(target.querySelector(".o_dialog footer button").textContent, "Ok");
    click(mainButtons[1]);
    await nextTick();
    assert.deepEqual(
        [...target.querySelectorAll("main .clearfix p")].map((el) => el.textContent),
        [
            "An error occurred",
            "Please use the copy button to report the error to your support service.",
            "Something bad happened",
        ]
    );
    assert.deepEqual(
        [...target.querySelectorAll("main .clearfix code")].map((el) => el.textContent),
        ["ERROR_NAME"]
    );
    assert.containsOnce(target, "div.o_error_detail");
    assert.strictEqual(
        target.querySelector("div.o_error_detail").textContent,
        "This is a traceback string"
    );
});

QUnit.test("button clipboard copy error traceback", async (assert) => {
    assert.expect(1);
    const error = new Error();
    error.name = "ERROR_NAME";
    error.message = "This is the message";
    error.traceback = "This is a traceback";
    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (value) => {
                    assert.strictEqual(
                        value,
                        `${error.name}\n${error.message}\n${error.traceback}`
                    );
                },
            },
        },
    });
    env = await makeDialogTestEnv();
    await mount(ErrorDialog, target, {
        env,
        props: {
            message: error.message,
            name: "ERROR_NAME",
            traceback: "This is a traceback",
            close() {},
        },
    });
    const clipboardButton = target.querySelector(".fa-clipboard");
    click(clipboardButton);
    await nextTick();
});

QUnit.test("WarningDialog", async (assert) => {
    assert.expect(6);
    assert.containsNone(target, ".o_dialog");
    env = await makeDialogTestEnv();
    await mount(WarningDialog, target, {
        env,
        props: {
            exceptionName: "odoo.exceptions.UserError",
            message: "...",
            data: { arguments: ["Some strange unreadable message"] },
            close() {},
        },
    });
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "User Error");
    assert.containsOnce(target, "main .o_dialog_warning");
    assert.strictEqual(target.querySelector("main").textContent, "Some strange unreadable message");
    assert.strictEqual(target.querySelector(".o_dialog footer button").textContent, "Ok");
});

QUnit.test("RedirectWarningDialog", async (assert) => {
    assert.expect(10);
    const faceActionService = {
        name: "action",
        start() {
            return {
                doAction(actionId) {
                    assert.step(actionId);
                },
            };
        },
    };
    serviceRegistry.add("action", faceActionService);
    env = await makeDialogTestEnv();
    assert.containsNone(target, ".o_dialog");
    await mount(RedirectWarningDialog, target, {
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
                assert.step("dialog-closed");
            },
        },
    });
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Odoo Warning");
    assert.strictEqual(target.querySelector("main").textContent, "Some strange unreadable message");
    const footerButtons = target.querySelectorAll("footer button");
    assert.deepEqual(
        [...footerButtons].map((el) => el.textContent),
        ["Buy book on cryptography", "Cancel"]
    );
    await click(footerButtons[0]); // click on "Buy book on cryptography"
    assert.verifySteps(["buy_action_id", "dialog-closed"]);

    await click(footerButtons[1]); // click on "Cancel"
    assert.verifySteps(["dialog-closed"]);
});

QUnit.test("Error504Dialog", async (assert) => {
    assert.expect(5);
    assert.containsNone(target, ".o_dialog");
    env = await makeDialogTestEnv();
    await mount(Error504Dialog, target, { env, props: { close() {} } });
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Request timeout");
    assert.strictEqual(
        target.querySelector("main p").textContent,
        " The operation was interrupted. This usually means that the current operation is taking too much time. "
    );
    assert.strictEqual(target.querySelector(".o_dialog footer button").textContent, "Ok");
});

QUnit.test("SessionExpiredDialog", async (assert) => {
    assert.expect(7);
    patchWithCleanup(browser, {
        location: {
            reload() {
                assert.step("location reload");
            },
        },
    });
    env = await makeDialogTestEnv();
    assert.containsNone(target, ".o_dialog");
    await mount(SessionExpiredDialog, target, { env, props: { close() {} } });
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(
        target.querySelector("header .modal-title").textContent,
        "Odoo Session Expired"
    );
    assert.strictEqual(
        target.querySelector("main p").textContent,
        " Your Odoo session expired. The current page is about to be refreshed. "
    );
    const footerButton = target.querySelector(".o_dialog footer button");
    assert.strictEqual(footerButton.textContent, "Ok");
    click(footerButton);
    assert.verifySteps(["location reload"]);
});
