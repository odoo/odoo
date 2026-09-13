// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CopyButton } from "@web/components/copy_button/copy_button";
import { browser } from "@web/core/browser/browser";

test("a clipboard write finishing after destruction does not open a tooltip", async () => {
    const write = new Deferred();
    patchWithCleanup(browser.navigator.clipboard, { writeText: () => write });
    const button = await mountWithCleanup(CopyButton, { props: { content: "copy" } });
    const pending = button.onClick();
    button.__owl__.app.destroy();
    write.resolve();
    await pending;
    expect(button.tooltipCloseTimer).toBe(undefined);
    expect(".o_popover").toHaveCount(0);
});

beforeEach(() => {
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(`writeText: ${text}`);
        },
        async write(object) {
            expect.step(
                `write: {${Object.entries(object)
                    .map(([k, v]) => k + ": " + v)
                    .join(", ")}}`,
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
    expect.verifySteps([
        "writeText: content to copy 1",
        "writeText: content to copy 2",
    ]);
});

test("copies an object via a function to the clipboard", async () => {
    /** @type {Record<string, string>} */
    let contentToCopy = { oneKey: "oneValue" };
    const content = () => contentToCopy;
    await mountWithCleanup(CopyButton, { props: { content } });
    await click(".o_clipboard_button");
    contentToCopy = { anotherKey: "anotherValue" };
    await click(".o_clipboard_button");
    expect.verifySteps([
        "write: {oneKey: oneValue}",
        "write: {anotherKey: anotherValue}",
    ]);
});

test("copies a string from an async function to the clipboard", async () => {
    const content = async () => "async content";
    await mountWithCleanup(CopyButton, { props: { content } });
    await click(".o_clipboard_button");
    expect.verifySteps(["writeText: async content"]);
});

test("copies an object from an async function to the clipboard", async () => {
    const content = async () => ({ oneKey: "oneValue" });
    await mountWithCleanup(CopyButton, { props: { content } });
    await click(".o_clipboard_button");
    expect.verifySteps(["write: {oneKey: oneValue}"]);
});

test("does not submit forms", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { CopyButton };
        static template = xml`
                <form t-on-submit="this.onSubmit">
                    <CopyButton content="'some text'"/>
                    <!-- note that type="submit" is implicit on the following button -->
                    <button class="submit-button"/>
                </form>
            `;
        onSubmit(/** @type {SubmitEvent} */ ev) {
            ev.preventDefault();
            expect.step("form submit");
        }
    }
    await mountWithCleanup(Parent);
    await click(".o_clipboard_button");
    expect.verifySteps(["writeText: some text"]);
    await click(".submit-button");
    expect.verifySteps(["form submit"]);
});

test("nothing to copy writes nothing and shows no tooltip", async () => {
    patchWithCleanup(browser.console, {
        warn: (...args) => expect.step(`warn: ${args.join(" ")}`),
    });
    await mountWithCleanup(CopyButton, { props: { content: () => undefined } });
    await click(".o_clipboard_button");
    expect.verifySteps([]);
    expect(".o_popover").toHaveCount(0);
});
