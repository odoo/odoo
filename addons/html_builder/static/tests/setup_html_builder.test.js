import {
    defineWebsiteModels,
    exampleWebsiteContent,
    getEditable,
    modifyText,
    setupWebsiteBuilder,
} from "./helpers";
import { BuilderSidebar } from "@html_builder/builder/builder_sidebar/builder_sidebar";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("setup of the editable elements", async () => {
    await setupWebsiteBuilder(getEditable('<h1 class="title">Hello</h1>'));
    expect(":iframe #wrap").toHaveClass("o_editable");
});

test("history back", async () => {
    let builder_sidebar;
    // Patch to get the builder sidebar instance
    patchWithCleanup(BuilderSidebar.prototype, {
        setup() {
            super.setup(...arguments);
            builder_sidebar = this;
        },
    });
    // Navigating back in the browser history should not lead to a warning popup
    // if the website was not edited.
    const { getEditor } = await setupWebsiteBuilder(getEditable(exampleWebsiteContent));
    builder_sidebar.onBeforeLeave();
    await animationFrame();
    expect(".modal-content:contains('If you proceed, your changes will be lost')").toHaveCount(0);
    // Navigating back in the browser history should lead to a warning popup if
    // the website was edited.
    await modifyText(getEditor());
    await animationFrame();
    builder_sidebar.onBeforeLeave();
    await animationFrame();
    expect(".modal-content:contains('If you proceed, your changes will be lost')").toHaveCount(1);
});
