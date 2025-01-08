import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "../helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

const dummySnippet = `
    <section data-name="Dummy Section">
        <div class="container">
            <div class="row">
                <div class="col-lg-7">
                    <p>TEST</p>
                </div>
                <div class="col-lg-5">
                    <p>TEST</p>
                </div>
            </div>
        </div>
    </section>
`;

test("Use the sidebar 'remove' buttons", async () => {
    await setupWebsiteBuilder(dummySnippet);

    const removeSectionSelector =
        ".o_customize_tab .options-container > div:contains('Dummy Section') button.oe_snippet_remove";
    const removeColumnSelector =
        ".o_customize_tab .options-container > div:contains('Column') button.oe_snippet_remove";

    await contains(":iframe .col-lg-7").click();
    expect(removeSectionSelector).toHaveCount(1);
    expect(removeColumnSelector).toHaveCount(1);

    await contains(removeColumnSelector).click();
    expect(":iframe .col-lg-7").toHaveCount(0);
    await contains(removeSectionSelector).click();
    expect(":iframe section").toHaveCount(0);
});

test("Use the sidebar 'clone' buttons", async () => {
    await setupWebsiteBuilder(dummySnippet);

    const cloneSectionSelector =
        ".o_customize_tab .options-container > div:contains('Dummy Section') button.oe_snippet_clone";
    const cloneColumnSelector =
        ".o_customize_tab .options-container > div:contains('Column') button.oe_snippet_clone";

    await contains(":iframe .col-lg-7").click();
    expect(cloneSectionSelector).toHaveCount(1);
    expect(cloneColumnSelector).toHaveCount(1);

    await contains(cloneColumnSelector).click();
    expect(":iframe .col-lg-7").toHaveCount(2);
    await contains(cloneSectionSelector).click();
    expect(":iframe section").toHaveCount(2);
    expect(":iframe .col-lg-7").toHaveCount(4);
    expect(":iframe .col-lg-5").toHaveCount(2);
});

test("Clicking on the options container title selects the corresponding element", async () => {
    await setupWebsiteBuilder(dummySnippet);

    await contains(":iframe .col-lg-7").click();
    expect(".o_customize_tab .options-container").toHaveCount(2);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .col-lg-7");

    await contains(".o_customize_tab .options-container span:contains('Dummy Section')").click();
    expect(".o_customize_tab .options-container").toHaveCount(1);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe section");
});

test("Show the overlay preview when hovering an options container", async () => {
    await setupWebsiteBuilder(dummySnippet);

    await contains(":iframe .col-lg-7").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".oe_overlay").toHaveCount(2);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .col-lg-7");

    await contains(".o_customize_tab .options-container span:contains('Dummy Section')").hover();
    expect(".overlay .o_overlay_options").toHaveCount(0);
    expect(".oe_overlay.oe_active.o_overlay_hidden").toHaveCount(1);
    expect(".oe_overlay.o_we_overlay_preview").toHaveRect(":iframe section");

    await contains(".o_customize_tab .options-container span:contains('Column')").hover();
    expect(".overlay .o_overlay_options").toHaveCount(0);
    expect(".oe_overlay.oe_active.o_we_overlay_preview").toHaveCount(1);
    expect(".oe_overlay.o_we_overlay_preview").toHaveRect(":iframe .col-lg-7");

    await contains(":iframe .col-lg-7").hover();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".oe_overlay.o_we_overlay_preview").toHaveCount(0);
    expect(".oe_overlay.oe_active:not(.o_overlay_hidden)").toHaveRect(":iframe .col-lg-7");
});
