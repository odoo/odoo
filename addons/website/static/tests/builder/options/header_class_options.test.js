import { expect, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// The header's scroll effect switches views: the header is rendered again by
// the server on click (not on hover), as with its other view options.
function header(views) {
    const effect = views["website.header_visibility_fixed"]
        ? "o_header_fixed"
        : "o_header_standard";
    return `<header id="top" class="${effect}" data-anchor="true" data-name="Header">
        <nav class="navbar"><div id="o_main_nav" class="o_main_nav container">Menu</div></nav>
    </header>`;
}

function mockRenders() {
    onRpc("/website/theme_customize_data_get", () => ["website.header_visibility_standard"]);
    onRpc("/blank", (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        expect.step("render");
        return new Response(
            `<html><body><div id="wrapwrap">${header(views)}<main></main></div></body></html>`
        );
    });
}

test("the header's content width is previewed on the elements printing it", async () => {
    mockRenders();
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${params.enable}`);
    });
    // Nested width elements (as the Rounded Box layout), and the mobile
    // header's container, which doesn't follow the setting.
    await setupWebsiteBuilder("", {
        headerContent: `<header id="top" data-anchor="true" data-name="Header">
            <div class="container o_header_content_width test-outer">
                <nav class="navbar"><div id="o_main_nav" class="o_main_nav container o_header_content_width">Menu</div></nav>
            </div>
            <nav class="o_header_mobile"><div class="container test-mobile">Mobile</div></nav>
        </header><main></main>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Content Width'] button[title='Small']").hover();
    expect(":iframe .test-outer").toHaveClass("o_container_small");
    expect(":iframe #o_main_nav").toHaveClass("o_container_small");
    expect(":iframe #o_main_nav").not.toHaveClass("container");
    expect(":iframe .test-mobile").not.toHaveClass("o_container_small");
    await contains("[data-label='Content Width'] button[title='Full']").click();
    expect(":iframe .test-outer").toHaveClass("container-fluid");
    expect(":iframe #o_main_nav").toHaveClass("container-fluid");
    expect("[data-label='Content Width'] button[title='Full']").toHaveClass("active");
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(":iframe #o_main_nav").toHaveClass("container");
    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    await runAllTimers();
    // Shown by the class: no render.
    expect.verifySteps([]);
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps(["write website.header_width_full"]);
});

test("the header's scroll effect renders on click, the header with its class", async () => {
    mockRenders();
    await setupWebsiteBuilder("", { headerContent: `${header({})}<main></main>` });
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Scroll Effect'] .dropdown-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Fixed')").click();
    await waitFor(":iframe header#top.o_header_fixed");
    await waitFor("[data-label='Scroll Effect'] .dropdown-toggle:contains('Fixed')");
    // Once rendered, the pick is committed.
    await waitFor(".o-snippets-top-actions button[data-icon='undo']:enabled");
    expect.verifySteps(["render", "render"]);
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    await waitFor(":iframe header#top.o_header_standard");
    await waitFor("[data-label='Scroll Effect'] .dropdown-toggle:contains('Standard')");
});
