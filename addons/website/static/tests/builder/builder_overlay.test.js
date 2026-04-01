import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

defineWebsiteModels();

test("Toggle the overlays when clicking on an option element", async () => {
    // TODO improve when more options will be defined.
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-3">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);
    await contains(":iframe section").click();
    expect(".oe_overlay").toHaveCount(1);
    expect(".oe_overlay").toHaveRect(":iframe section");

    await contains(":iframe .col-lg-3").click();
    expect(".oe_overlay").toHaveCount(2);
    expect(".oe_overlay.oe_active").toHaveCount(1);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .col-lg-3");
});

test("Refresh the overlays when their target size changes", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-3" style="height: 20px;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);
    await contains(":iframe .col-lg-3").click();
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .col-lg-3");

    queryOne(":iframe .col-lg-3").style.height = "50px";
    await animationFrame();
    expect(".oe_overlay.oe_active").toHaveStyle({ height: "50px" });
});

test("Resize vertically (sizingY)", async () => {
    await setupWebsiteBuilder(
        `
        <section style>
            <div class="container">
                <div class="row">
                    <div class="col-lg-3" style="height: 40px;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );
    await contains(":iframe section").click();
    expect(".oe_overlay.oe_active").toHaveCount(1);

    const nHandleSelector = ".oe_overlay .o_handle.n:not(.o_grid_handle)";
    let dragActions = await contains(nHandleSelector).drag({ position: { x: 0, y: 0 } });
    await dragActions.moveTo(nHandleSelector, { position: { x: 0, y: 80 } });
    await dragActions.drop();
    expect(":iframe section").toHaveClass("pt80");
    expect(".oe_overlay").toHaveRect(":iframe section");

    const sHandleSelector = ".oe_overlay .o_handle.s:not(.o_grid_handle)";
    dragActions = await contains(sHandleSelector).drag({ position: { x: 0, y: 120 } });
    await dragActions.moveTo(sHandleSelector, { position: { x: 0, y: 160 } });
    await dragActions.drop();
    expect(":iframe section").toHaveClass("pt80 pb40");
    expect(".oe_overlay").toHaveRect(":iframe section");
});

test("Resize horizontally (sizingX)", async () => {
    await setupWebsiteBuilder(
        `
        <section style="width: 600px;">
            <div class="container">
                <div class="row">
                    <div class="col-lg-6">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );
    await contains(":iframe .col-lg-6").click();
    expect(".oe_overlay.oe_active").toHaveCount(1);

    const eHandleSelector = ".oe_overlay.oe_active .o_handle.e:not(.o_grid_handle)";
    let dragActions = await contains(eHandleSelector).drag({ position: { x: 300, y: 0 } });
    await dragActions.moveTo(eHandleSelector, { position: { x: 600, y: 0 } });
    await dragActions.drop();
    expect(":iframe .row > div").toHaveClass("col-lg-12");
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .row > div");

    const wHandleSelector = ".oe_overlay.oe_active .o_handle.w:not(.o_grid_handle)";
    dragActions = await contains(wHandleSelector).drag({ position: { x: 0, y: 0 } });
    await dragActions.moveTo(wHandleSelector, { position: { x: 600, y: 0 } });
    await dragActions.drop();
    expect(":iframe .row > div").toHaveClass("col-lg-1 offset-lg-11");
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .row > div");
});

// TODO to fix issue hoot (after rebase)?
test("Resize in grid mode (sizingGrid)", async () => {
    await setupWebsiteBuilder(
        `
        <section style="width: 600px;">
            <div class="container p-0">
                <div class="row o_grid_mode" data-row-count="4">
                    <div class="o_grid_item g-height-4 g-col-lg-6 col-lg-6" style="grid-area: 1 / 1 / 5 / 7;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );
    await contains(":iframe .col-lg-6").click();
    expect(".oe_overlay.oe_active").toHaveCount(1);

    const eHandleSelector = ".oe_overlay.oe_active .o_grid_handle.e";
    let dragActions = await contains(eHandleSelector).drag({ position: { x: 300, y: 100 } });
    await dragActions.moveTo(eHandleSelector, { position: { x: 600, y: 100 } });
    await dragActions.drop();
    expect(":iframe .o_grid_item").toHaveClass("g-col-lg-12 col-lg-12");
    expect(":iframe .o_grid_item").toHaveStyle({ gridArea: "1 / 1 / 5 / 13" });
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .o_grid_item");

    const wHandleSelector = ".oe_overlay.oe_active .o_grid_handle.w";
    dragActions = await contains(wHandleSelector).drag({ position: { x: 0, y: 100 } });
    await dragActions.moveTo(eHandleSelector, { position: { x: 600, y: 100 } });
    await dragActions.drop();
    expect(":iframe .o_grid_item").toHaveClass("g-col-lg-1 col-lg-1");
    expect(":iframe .o_grid_item").toHaveStyle({ gridArea: "1 / 12 / 5 / 13" });
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .o_grid_item");

    const nHandleSelector = ".oe_overlay.oe_active .o_grid_handle.n";
    dragActions = await contains(nHandleSelector).drag({ position: { x: 575, y: 0 } });
    await dragActions.moveTo(nHandleSelector, { position: { x: 0, y: 300 } });
    await dragActions.drop();
    expect(":iframe .o_grid_item").toHaveClass("g-col-lg-1 col-lg-1 g-height-1");
    expect(":iframe .o_grid_item").toHaveStyle({ gridArea: "4 / 12 / 5 / 13" });
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .o_grid_item");

    const sHandleSelector = ".oe_overlay.oe_active .o_grid_handle.s";
    dragActions = await contains(sHandleSelector).drag({ position: { x: 575, y: 200 } });
    await dragActions.moveTo(sHandleSelector, { position: { x: 0, y: 300 } });
    await dragActions.drop();
    expect(":iframe .o_grid_item").toHaveClass("g-col-lg-1 col-lg-1 g-height-3");
    expect(":iframe .o_grid_item").toHaveStyle({ gridArea: "4 / 12 / 7 / 13" });
    expect(":iframe .row").toHaveAttribute("data-row-count", "6");
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .o_grid_item");
});

test("Mouse move on throttleForAnimation", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-3">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);

    await contains(":iframe .col-lg-3").click();
    expect(".oe_overlay.oe_active").toHaveCount(1);

    const keyDownEvent = new KeyboardEvent("keydown", { bubbles: true });
    const mouseMoveEvent = new KeyboardEvent("mousemove", { bubbles: true });
    const p = queryOne(":iframe p:not([data-selection-placeholder])");

    p.dispatchEvent(keyDownEvent);
    expect(".oe_overlay.oe_active.o_overlay_hidden").toHaveCount(1);
    p.dispatchEvent(mouseMoveEvent);
    expect(".oe_overlay.oe_active:not(.o_overlay_hidden)").toHaveCount(1);
    p.dispatchEvent(keyDownEvent);
    expect(".oe_overlay.oe_active.o_overlay_hidden").toHaveCount(1);
    p.dispatchEvent(mouseMoveEvent);
    // Due to throttleForAnimation, the second mousemove event listener call
    // will be throttled at animationFrame time
    await animationFrame();
    expect(".oe_overlay.oe_active:not(.o_overlay_hidden)").toHaveCount(1);
});
