import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { getDragHelper, waitForEndOfOperation } from "@html_builder/../tests/helpers";

defineWebsiteModels();

test("Cloning a grid item should shift the clone and put it in front of the others", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row o_grid_mode" data-row-count="4">
                    <div class="o_grid_item g-height-4 g-col-lg-7 col-lg-7" style="grid-area: 1 / 1 / 5 / 8; z-index: 1;">
                        <p>TEST</p>
                    </div>
                    <div class="o_grid_item g-height-2 g-col-lg-5 col-lg-5" style="grid-area: 1 / 8 / 3 / 13; z-index: 2;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);

    await contains(":iframe .g-col-lg-7").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    await contains(".overlay .o_snippet_clone").click();
    expect(":iframe .col-lg-7:nth-child(2)").toHaveCount(1);
    expect(":iframe .col-lg-7:nth-child(2)").toHaveStyle({
        gridArea: "2 / 2 / 6 / 9",
        zIndex: "3",
    });
    expect(":iframe .o_grid_mode").toHaveAttribute("data-row-count", "5");

    await contains(":iframe .g-col-lg-5").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    await contains(".overlay .o_snippet_clone").click();

    expect(":iframe .col-lg-5:nth-child(4)").toHaveCount(1);
    expect(":iframe .col-lg-5:nth-child(4)").toHaveStyle({
        gridArea: "2 / 1 / 4 / 6",
        zIndex: "4",
    });
    expect(":iframe .o_grid_mode").toHaveAttribute("data-row-count", "5");
});

test("Drag & drop an inner snippet inside a grid item should adjust its height on preview and on drop", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="container">
                <div class="row o_grid_mode" data-row-count="1">
                    <div class="o_grid_item g-height-1 g-col-lg-7 col-lg-7" style="grid-area: 1 / 1 / 2 / 8; z-index: 1;">
                        <p style="height: 50px;">TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `,
        { loadIframeBundles: true }
    );

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .btn").toHaveCount(1);
    expect(":iframe .o_grid_item").toHaveClass("g-height-3");
    expect(":iframe .o_grid_mode").toHaveAttribute("data-row-count", "3");

    await drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .btn").toHaveCount(1);
    expect(":iframe .o_grid_item").toHaveClass("g-height-3");
    expect(":iframe .o_grid_mode").toHaveAttribute("data-row-count", "3");
});
