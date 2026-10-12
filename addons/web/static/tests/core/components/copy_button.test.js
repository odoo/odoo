import { CopyButton } from "@web/core/copy_button/copy_button";
import { browser } from "@web/core/browser/browser";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";

beforeEach(() => {
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(`writeText: ${text}`);
        },
        async write(object) {
            expect.step(
                `write: {${Object.entries(object)
                    .map(([k, v]) => k + ": " + v)
                    .join(", ")}}`
            );
        },
    });
});

test("copies a string to the clipboard", async () => {
    await mountWithCleanup(CopyButton, { props: { content: "content to copy" } });
    await click(".o_clipboard_button");
    expect.verifySteps(["writeText: content to copy"]);
});

test("copies an object to the clipboard", async () => {
    await mountWithCleanup(CopyButton, { props: { content: { oneKey: "oneValue" } } });
    await click(".o_clipboard_button");
    expect.verifySteps(["write: {oneKey: oneValue}"]);
});

test("copies a string via a function to the clipboard", async () => {
    let contentToCopy = "content to copy 1";
    const content = () => contentToCopy;
    await mountWithCleanup(CopyButton, { props: { content } });
    await click(".o_clipboard_button");
    contentToCopy = "content to copy 2";
    await click(".o_clipboard_button");
    expect.verifySteps(["writeText: content to copy 1", "writeText: content to copy 2"]);
});

test("copies an object via a function to the clipboard", async () => {
    let contentToCopy = { oneKey: "oneValue" };
    const content = () => contentToCopy;
    await mountWithCleanup(CopyButton, { props: { content } });
    await click(".o_clipboard_button");
    contentToCopy = { anotherKey: "anotherValue" };
    await click(".o_clipboard_button");
    expect.verifySteps(["write: {oneKey: oneValue}", "write: {anotherKey: anotherValue}"]);
});
