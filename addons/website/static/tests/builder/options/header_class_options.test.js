import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// The header's scroll effect and content width switch views: the header is
// rendered again by the server on click (not on hover), as with its other
// view options.
function header(views) {
    const effect = views["website.header_visibility_fixed"]
        ? "o_header_fixed"
        : "o_header_standard";
    const width = views["website.header_width_small"] ? "o_container_small" : "container";
    return `<header id="top" class="${effect}" data-anchor="true" data-name="Header">
        <nav class="navbar"><div id="o_main_nav" class="o_main_nav ${width}">Menu</div></nav>
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

test("the header's content width renders on click, not on hover", async () => {
    mockRenders();
    await setupWebsiteBuilder("", { headerContent: `${header({})}<main></main>` });
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Content Width'] button[title='Small']").hover();
    await runAllTimers();
    expect.verifySteps([]);
    await contains("[data-label='Content Width'] button[title='Small']").click();
    await waitFor(":iframe #o_main_nav.o_container_small");
    await waitFor("[data-label='Content Width'] button[title='Small'].active");
    expect.verifySteps(["render", "render"]);
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    await waitFor(":iframe #o_main_nav.container");
});

test("the header's scroll effect renders on click, the header with its class", async () => {
    mockRenders();
    await setupWebsiteBuilder("", { headerContent: `${header({})}<main></main>` });
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Scroll Effect'] .dropdown-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Fixed')").click();
    await waitFor(":iframe header#top.o_header_fixed");
    // Once rendered, the pick is committed.
    await waitFor("[data-label='Scroll Effect'] .dropdown-toggle:contains('Fixed')");
    expect.verifySteps(["render", "render"]);
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    await waitFor(":iframe header#top.o_header_standard");
    await waitFor("[data-label='Scroll Effect'] .dropdown-toggle:contains('Standard')");
});
