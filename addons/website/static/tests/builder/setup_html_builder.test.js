import {
    defineWebsiteModels,
    exampleWebsiteContent,
    modifyText,
    setupWebsiteBuilder,
} from "./website_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { patchWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { WebsiteBuilder } from "@website/builder/website_builder";

defineWebsiteModels();

test("setup of the editable elements", async () => {
    await setupWebsiteBuilder('<h1 class="title">Hello</h1>');
    expect(":iframe #wrap").toHaveClass("o_editable");
});

test("history back", async () => {
    let builder;
    // Patch to get the builder sidebar instance
    patchWithCleanup(WebsiteBuilder.prototype, {
        setup() {
            super.setup(...arguments);
            builder = this;
        },
    });
    // Navigating back in the browser history should not lead to a warning popup
    // if the website was not edited.
    const { getEditor, getEditableContent } = await setupWebsiteBuilder(exampleWebsiteContent);
    builder.onBeforeLeave();
    await animationFrame();
    expect(".modal-content:contains('If you proceed, your changes will be lost')").toHaveCount(0);
    // Navigating back in the browser history should lead to a warning popup if
    // the website was edited.
    await modifyText(getEditor(), getEditableContent());
    await animationFrame();
    builder.onBeforeLeave();
    await animationFrame();
    expect(".modal-content:contains('If you proceed, your changes will be lost')").toHaveCount(1);
});

test("Set and update the 'contenteditable' attribute on the editable elements", async () => {
    const { getEditor, getEditableContent } = await setupWebsiteBuilder(
        "<section><p>TEST</p></section>"
    );
    const wrapwrapEl = getEditor().editable;
    const wrapEl = getEditableContent();
    expect(wrapwrapEl.getAttribute("contenteditable")).toBe("false");
    expect(wrapEl.getAttribute("contenteditable")).toBe("true");

    await contains(":iframe section").click();
    await contains(".overlay .oe_snippet_remove").click();
    expect(wrapwrapEl.getAttribute("contenteditable")).toBe("false");
    expect(wrapEl.getAttribute("contenteditable")).toBe("false");
});

test("Admin navbar is hidden in edit mode", async () => {
    await setupWebsiteBuilder("<section><p>TEST</p></section>");
    await waitFor(":iframe section");
    expect(".o_main_navbar").not.toBeVisible();
});
