import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("Content editable test", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="not_a_container_class">
                <div class="container"></div>
            </div>
        </section>
        <section><div class="o_container_small"></div></section>
        <section><div class="container-fluid"></div></section>
        <section>
            <div class="container">
                <div class="o_we_bg_filter"></div>
                <div class="o_we_shape"></div>
            </div>
        </section>
    `);
    expect(":iframe section:not([contenteditable=false]) > .not_a_container_class").toHaveCount(1);
    expect(":iframe section[contenteditable=false] > .o_container_small[contenteditable=true]").toHaveCount(1);
    expect(":iframe section[contenteditable=false] > .container-fluid[contenteditable=true]").toHaveCount(1);
    expect(":iframe section[contenteditable=false] > .container[contenteditable=true]").toHaveCount(1);
    expect(":iframe .o_we_bg_filter[contenteditable=false]").toHaveCount(1);
    expect(":iframe .o_we_shape[contenteditable=false]").toHaveCount(1);

    onRpc("ir.ui.view", "save", ({ args }) => {
        // should not contain any contenteditable when saving
        expect(args[1].includes("contenteditable")).toBe(false);
        return true;
    });
    queryOne(":iframe .o_container_small").textContent = "dirty for save";
    await contains(".o-snippets-top-actions [data-action='save']").click();
});
