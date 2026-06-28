import { expect, test } from "@odoo/hoot";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { click, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { MassMailingLinkPlugin } from "../src/editor/plugins/mass_mailing_link_plugin";

const config = {
    Plugins: [...MAIN_PLUGINS].filter((p) => p.id != "link").concat(MassMailingLinkPlugin),
};

defineMailModels();

test("disable link tracking option should be shown and diable/enable link tracking when checked/unchecked respectively.", async () => {
    const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>', {
        config,
    });
    // Click on the link to open link popover
    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    // Open advanced mode
    await contains(".o_link_popover_container button[title='Advanced mode']").click();
    // Check the disable link tracking option
    await contains(
        ".o_seo_option_row:has(span[title='Send the original url instead of wrapping it into a tracking url.']) input[type='checkbox']"
    ).click();
    // Go back to main popover view
    await click("button.fa-angle-left");
    // Apply
    await contains("button.o_we_apply_link").click();

    expect(el.querySelector("a")).toHaveAttribute("data-no-tracking");

    // Click on the link to open link popover
    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    // Open advanced mode
    await contains(".o_link_popover_container button[title='Advanced mode']").click();
    // Check the disable link tracking option
    await contains(
        ".o_seo_option_row:has(span[title='Send the original url instead of wrapping it into a tracking url.']) input[type='checkbox']"
    ).click();
    // Go back to main popover view
    await click("button.fa-angle-left");
    // Apply
    await contains("button.o_we_apply_link").click();

    expect(el.querySelector("a")).not.toHaveAttribute("data-no-tracking");
});
