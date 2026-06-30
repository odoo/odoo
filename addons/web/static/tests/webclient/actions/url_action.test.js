import { expect, test } from "@odoo/hoot";
import { getService, makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

test("execute an 'ir.actions.act_url' action with target 'self'", async () => {
    patchWithCleanup(browser.location, {
        assign: (url) => {
            expect.step(url);
        },
    });
    await makeMockEnv();
    await getService("action").doAction({
        type: "ir.actions.act_url",
        target: "self",
        url: "/my/test/url",
    });
    expect.verifySteps(["/my/test/url"]);
});

test("execute an 'ir.actions.act_url' action with onClose option", async () => {
    patchWithCleanup(browser, {
        open: () => expect.step("browser open"),
    });
    await makeMockEnv();
    const options = {
        onClose: () => expect.step("onClose"),
    };
    await getService("action").doAction({ type: "ir.actions.act_url" }, options);
    expect.verifySteps(["browser open", "onClose"]);
});

test("execute an 'ir.actions.act_url' action with url javascript:", async () => {
    patchWithCleanup(browser.location, {
        assign: (url) => {
            expect.step(url);
        },
    });
    await makeMockEnv();
    await getService("action").doAction({
        type: "ir.actions.act_url",
        target: "self",
        url: "javascript:alert()",
    });
    expect.verifySteps(["/javascript:alert()"]);
});

test("execute an 'ir.actions.act_url' action with target 'download'", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(url);
        },
    });
    await makeMockEnv();
    await getService("action").doAction({
        type: "ir.actions.act_url",
        target: "download",
        url: "/my/test/url",
    });
    expect(".o_blockUI").toHaveCount(0);
    expect.verifySteps(["/my/test/url"]);
});
