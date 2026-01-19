import { expect, queryOne, test, waitFor } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

test("reload from 'theme' tab should stay on 'theme'", async () => {
    onRpc("ir.ui.view", "save", () => {
        expect.step("save");
        return true;
    });
    onRpc("/website/theme_customize_data", () => {});
    await setupWebsiteBuilder(`<div class="test">b</div>`);
    queryOne(":iframe .test").dataset.applied = "1";
    expect(":iframe .test").toHaveAttribute("data-applied");

    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await waitFor(".o_theme_tab");
    expect(".o-snippets-tabs button[data-name=theme]").toHaveClass("active");
    await contains("div.hb-row:contains(Show Header) input[type=checkbox]").click();

    expect.verifySteps(["save"]);
    // NOTE: the goal of the following assertion is to ensure that the relaod is
    // completed. This relies on the "save" mocked for this test that does
    // nothing to save anything and the reload (mocked in `setupWebsiteBuilder`)
    // resets to initial content
    expect(":iframe .test").not.toHaveAttribute("data-applied");

    expect(".o-snippets-tabs button[data-name=theme]").toHaveClass("active");
});

test("hide invisible element after reload from 'theme' tab should stay on 'theme'", async () => {
    onRpc("ir.ui.view", "save", () => {
        expect.step("save");
        return true;
    });
    onRpc("/website/theme_customize_data", () => {});
    await setupWebsiteBuilder(
        `<div class="s_invisible_el o_snippet_invisible" data-name="Invisible Element"></div>`
    );
    queryOne(":iframe .s_invisible_el").dataset.applied = "1";
    expect(":iframe .s_invisible_el").toHaveAttribute("data-applied");

    await contains(
        ".o_we_invisible_el_panel  .o_we_invisible_entry:contains('Invisible Element') i.fa-eye"
    ).click();
    expect(":iframe .o_snippet_invisible").toHaveAttribute("data-invisible", "1");

    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await waitFor(".o_theme_tab");
    expect(".o-snippets-tabs button[data-name=theme]").toHaveClass("active");
    await contains("div.hb-row:contains(Show Header) input[type=checkbox]").click();

    await expect.waitForSteps(["save"]);
    // NOTE: the goal of the following assertion is to ensure that the relaod is
    // completed. This relies on the "save" mocked for this test that does
    // nothing to save anything and the reload (mocked in `setupWebsiteBuilder`)
    // resets to initial content
    expect(":iframe .o_snippet_invisible").not.toHaveAttribute("data-invisible", "1");

    expect(".o-snippets-tabs button[data-name=theme]").toHaveClass("active");

    await contains(
        ".o_we_invisible_el_panel  .o_we_invisible_entry:contains('Invisible Element') i.fa-eye"
    ).click();
    expect(":iframe .s_invisible_el").not.toHaveAttribute("data-applied");

    expect(
        ".o_we_invisible_el_panel  .o_we_invisible_entry:contains('Invisible Element') i"
    ).toHaveClass("fa-eye-slash");
    expect(".o-snippets-tabs button[data-name=theme]").toHaveClass("active");
});
