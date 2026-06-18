import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

// TODO Re-enable once interactions run within iframe in hoot tests.
// Note: without interactions within the iframe, this test will fail because the
// alert message is not rendered.
test.skip("alert message displayed if floating blocks has no cards", async () => {
    await setupWebsiteBuilderWithSnippet("s_floating_blocks");
    await contains(":iframe .s_floating_blocks_block").click();
    await contains(".options-container[data-container-title='Card'] .oe_snippet_remove").click();
    await contains(":iframe .s_floating_blocks_block").click();
    await contains(".options-container[data-container-title='Card'] .oe_snippet_remove").click();
    await contains(":iframe .s_floating_blocks_block").click();
    await contains(".options-container[data-container-title='Card'] .oe_snippet_remove").click();
    expect(":iframe .s_floating_blocks_alert_empty").toHaveCount(1);
    expect(":iframe .s_floating_blocks_alert_empty").toBeVisible();
});

test("Empty floating blocks snippet is removed on save", async () => {
    const resultSave = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        resultSave.push(args[1]);
        return true;
    });

    await setupWebsiteBuilder(`
        <section class="s_floating_blocks" data-snippet="s_floating_blocks" data-name="Floating Blocks">
            <div class="s_floating_blocks_wrapper">
            </div>
        </section>
        <section class="s_text_block dummy-target" data-snippet="s_text_block" data-name="Text Block">
            <p>Delete me to dirty the editor</p>
        </section>
    `);
    // Deleting dummy text block to dirty the editor and activate save button.
    await contains(":iframe .dummy-target").click();
    await contains(".oe_snippet_remove").click();

    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave[0]).not.toInclude("s_floating_blocks");
});
