import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("Use the 'move arrows' overlay buttons", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-5">
                        <p>TEST</p>
                    </div>
                    <div class="col-lg-4">
                        <p>TEST</p>
                    </div>
                    <div class="col-lg-3">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        <section>
            <p>TEST</p>
        </section>
    `,
        { loadIframeBundles: true }
    );

    await contains(":iframe section").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .fa-angle-down").toHaveCount(1);
    expect(".overlay .fa-angle-up").toHaveCount(0);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);

    await contains(":iframe .col-lg-5").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(0);
    expect(".overlay .fa-angle-up, .overlay .fa-angle-down").toHaveCount(0);

    await contains(":iframe .col-lg-3").click();
    expect(".overlay .fa-angle-right").toHaveCount(0);
    expect(".overlay .fa-angle-left").toHaveCount(1);

    await contains(":iframe .col-lg-4").click();
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(1);

    await contains(".overlay .fa-angle-left").click();
    expect(":iframe .col-lg-4:nth-child(1)").toHaveCount(1);
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(0);
});

test("Use the 'grid' overlay buttons", async () => {
    await setupWebsiteBuilder(
        `
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
    `,
        { loadIframeBundles: true }
    );

    await contains(":iframe .g-col-lg-5").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .o_send_back").toHaveCount(1);
    expect(".overlay .o_bring_front").toHaveCount(1);

    await contains(".overlay .o_send_back").click();
    expect(":iframe .g-col-lg-5").toHaveStyle({ zIndex: "0" });

    await contains(".overlay .o_bring_front").click();
    expect(":iframe .g-col-lg-5").toHaveStyle({ zIndex: "2" });
});
