import { defineWebsiteModels, openSnippetsMenu, setupWebsiteBuilder, getEditable } from "./helpers";
import { expect, test } from "@odoo/hoot";

defineWebsiteModels();

test("setup of the editable elements", async () => {
    await setupWebsiteBuilder(getEditable('<h1 class="title">Hello</h1>'));
    await openSnippetsMenu();
    expect(":iframe #wrap").toHaveClass("o_editable");
});
