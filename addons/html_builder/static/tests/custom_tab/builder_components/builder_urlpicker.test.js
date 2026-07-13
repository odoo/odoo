import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BuilderUrlPicker } from "@html_builder/core/building_blocks/builder_urlpicker";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

function setupUrlPickerTest() {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderUrlPicker action="'customUrlAction'"/>`;
            static components = { BuilderUrlPicker };
        }
    );

    addBuilderAction({
        customUrlAction: class extends BuilderAction {
            static id = "customUrlAction";
            setup() {
                this.preview = false;
            }
            apply({ editingElement, value }) {
                if (value) {
                    editingElement.setAttribute("href", value);
                } else {
                    editingElement.removeAttribute("href");
                }
            }
            getValue({ editingElement }) {
                return editingElement.getAttribute("href") || "";
            }
        },
    });
}

test("BuilderUrlPicker normalizes URL values before committing", async () => {
    setupUrlPickerTest();

    await setupHTMLBuilder(`<div class="test-options-target">Target</div>`);
    await contains(":iframe .test-options-target").click();
    const targetEl = queryOne(":iframe .test-options-target");

    const testCases = [
        ["odoo.com", "https://odoo.com"],
        ["ftp://odoo.com", "ftp://odoo.com"],
        ["http://odoo.com", "http://odoo.com"],
        ["https://odoo.com", "https://odoo.com"],
        ["test@test.com", "mailto:test@test.com"],
        ["mailto:test2@test.com", "mailto:test2@test.com"],
        ["+1555-555-5556", "tel:+1555-555-5556"],
        ["tel:+1 555-555-5557", "tel:+1 555-555-5557"],
        ["/hello", "/hello"],
        ["#top", "#top"],
    ];

    for (const [url, expectedUrl] of testCases) {
        await contains("[data-action-id='customUrlAction'] input").edit(url);
        expect(targetEl).toHaveAttribute("href", expectedUrl);
    }
});

test("BuilderUrlPicker preserves the current HTTP protocol when committing a bare domain", async () => {
    setupUrlPickerTest();

    await setupHTMLBuilder(
        `<div class="test-options-target" href="http://old.example.com">Target</div>`
    );
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customUrlAction'] input").edit("odoo.com");

    expect(queryOne(":iframe .test-options-target")).toHaveAttribute("href", "http://odoo.com");
    expect("[data-action-id='customUrlAction'] input").toHaveValue("http://odoo.com");
});

test("BuilderUrlPicker opens the normalized URL from the preview button", async () => {
    patchWithCleanup(window, {
        open: (url, target) => expect.step(`${url} ${target}`),
    });
    setupUrlPickerTest();

    await setupHTMLBuilder(`<div class="test-options-target">Target</div>`);
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customUrlAction'] input").fill("odoo.com");
    await contains("[data-action-id='customUrlAction'] button").click();

    expect.verifySteps(["https://odoo.com _blank"]);
});
