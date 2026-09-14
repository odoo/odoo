import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { Sidebar } from "@portal/interactions/sidebar";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

class PrintSidebar extends Sidebar {
    static selector = ".test-sidebar";
}

test("menu regeneration preserves document anchors and cleans up only its own nodes", async () => {
    const { core } = await startInteraction(
        PrintSidebar,
        `
        <div class="test-sidebar" id="document-owner">
            <ul class="bs-sidenav"><li class="static-link">Existing link</li></ul>
            <div id="quote_content">
                <div id="quote_existing">Existing anchor</div>
                <h3 id="details">Pricing</h3>
                <h2>Order <strong>SO001</strong><!-- internal annotation --></h2>
                <h3>Terms</h3>
            </div>
        </div>`,
    );
    const sidebar = getInteraction(core, PrintSidebar);
    sidebar.spyWatched = sidebar.el;
    sidebar.generateMenu({ maxWidth: "200px" });
    const generatedId = queryOne("h2").id;
    sidebar.generateMenu({ maxWidth: "200px" });
    expect(".bs-sidenav > li").toHaveCount(3);
    expect('.bs-sidenav a[href="#details"]').toHaveText("Pricing");
    expect(".bs-sidenav ul a").toHaveText("Terms");
    expect(`.bs-sidenav a[href="#${generatedId}"]`).toHaveText("Order SO001");
    expect("h2").toHaveAttribute("id", generatedId);
    expect("#quote_existing").toHaveCount(1);
    expect("#document-owner").toHaveCount(1);
    expect(".bs-sidenav a").toHaveStyle({ maxWidth: "200px" });
    core.stopInteractions();
    expect(".bs-sidenav > li").toHaveCount(1);
    expect("h2").not.toHaveAttribute("id");
    expect("#details").toHaveCount(1);
    expect("[data-anchor]").toHaveCount(0);
});

test("repeated print requests wait for the iframe to load", async () => {
    const { core } = await startInteraction(
        PrintSidebar,
        '<div class="test-sidebar"></div>',
    );
    const sidebar = getInteraction(core, PrintSidebar);
    sidebar.printIframeContent("about:blank#first");
    const frame = sidebar.printContent;
    patchWithCleanup(frame.contentWindow, { print: () => expect.step("print") });
    sidebar.printIframeContent("about:blank#first");
    expect.verifySteps([]);
    frame.dispatchEvent(new Event("load"));
    expect.verifySteps(["print"]);
    sidebar.printIframeContent("about:blank#first");
    expect.verifySteps(["print"]);
    core.stopInteractions();
});

test("a new print target replaces the cached iframe", async () => {
    const { core } = await startInteraction(
        PrintSidebar,
        '<div class="test-sidebar"></div>',
    );
    const sidebar = getInteraction(core, PrintSidebar);
    sidebar.printIframeContent("about:blank#first");
    patchWithCleanup(sidebar.printContent.contentWindow, {
        print: () => expect.step("stale print"),
    });
    sidebar.printIframeContent("about:blank#second");
    expect(sidebar.printContent.getAttribute("src")).toBe("about:blank#second");
    expect("iframe").toHaveCount(1);
    expect.verifySteps([]);
    core.stopInteractions();
});
