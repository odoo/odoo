import { CopyButton } from "@web/core/copy_button/copy_button";
import { browser } from "@web/core/browser/browser";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";

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
        onSubmit(ev) {
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
