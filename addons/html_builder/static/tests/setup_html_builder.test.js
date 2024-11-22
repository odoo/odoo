import {
    defineWebsiteModels,
    exampleWebsiteContent,
    getEditable,
    modifyText,
    setupWebsiteBuilder,
} from "./helpers";
import { SnippetsMenu } from "@html_builder/builder/snippets_menu";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("setup of the editable elements", async () => {
    await setupWebsiteBuilder(getEditable('<h1 class="title">Hello</h1>'));
    expect(":iframe #wrap").toHaveClass("o_editable");
});

test("history back", async () => {
    let snippetsMenu;
    // Patch to get the snippets menu instance
    patchWithCleanup(SnippetsMenu.prototype, {
        setup() {
            super.setup(...arguments);
            snippetsMenu = this;
        },
    });
    // Navigating back in the browser history should not lead to a warning popup
    // if the website was not edited.
    const { getEditor } = await setupWebsiteBuilder(getEditable(exampleWebsiteContent));
    snippetsMenu.onBeforeLeave();
    await animationFrame();
    expect(".modal-content:contains('If you proceed, your changes will be lost')").toHaveCount(0);
    // Navigating back in the browser history should lead to a warning popup if
    // the website was edited.
    await modifyText(getEditor());
    await animationFrame();
    snippetsMenu.onBeforeLeave();
    await animationFrame();
    expect(".modal-content:contains('If you proceed, your changes will be lost')").toHaveCount(1);
});
