import { expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// The scroll effect and the content width switch views that only set classes
// of the header: the builder shows them by the class, without a render.
// The content width's class is on the header's own containers, not on the
// mobile header's nor on the header's editable content.
const headerContent = `
    <header id="top" class="o_header_standard" data-anchor="true" data-name="Header">
        <nav class="navbar">
            <div id="o_main_nav" class="container o_main_nav">
                <div class="oe_structure">
                    <section class="s_text_block" data-snippet="s_text_block">
                        <div class="container">Call to action</div>
                    </section>
                </div>
            </div>
        </nav>
        <nav class="navbar o_header_mobile">
            <div class="o_main_nav container">Mobile</div>
        </nav>
    </header>`;

function mockViews() {
    onRpc("/website/theme_customize_data_get", () => ["website.header_visibility_standard"]);
    onRpc("/blank", () => {
        expect.step("render");
        return new Response(`<html><body><div id="wrapwrap"></div></body></html>`);
    });
}

async function pickScrollEffect(label) {
    await contains("[data-label='Scroll Effect'] .dropdown-toggle").click();
    await contains(`.o_popover .dropdown-item:contains('${label}')`).click();
}

test("a scroll effect is the header's class, undone with it, without a render", async () => {
    mockViews();
    await setupWebsiteBuilder("", { headerContent });
    await contains(":iframe #wrapwrap > header").click();
    await pickScrollEffect("Fixed");
    expect(":iframe header#top").toHaveClass("o_header_fixed");
    expect(":iframe header#top").not.toHaveClass("o_header_standard");
    await pickScrollEffect("Standard");
    expect(":iframe header#top").toHaveClass("o_header_standard");
    expect("[data-label='Scroll Effect'] .dropdown-toggle").toHaveText("Standard");
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(":iframe header#top").toHaveClass("o_header_fixed");
    expect("[data-label='Scroll Effect'] .dropdown-toggle").toHaveText("Fixed");
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(":iframe header#top").toHaveClass("o_header_standard");
    expect("[data-label='Scroll Effect'] .dropdown-toggle").toHaveText("Standard");
    await runAllTimers();
    expect.verifySteps([]);
});

test("the content width is the class of the header's own containers", async () => {
    mockViews();
    await setupWebsiteBuilder("", { headerContent });
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Content Width'] button[title='Small']").hover();
    expect(":iframe #o_main_nav").toHaveClass("o_container_small");
    await contains("[data-label='Content Width'] button[title='Small']").click();
    expect(":iframe #o_main_nav").toHaveClass("o_container_small");
    expect(":iframe #o_main_nav").not.toHaveClass("container");
    expect(":iframe .s_text_block > div").toHaveClass("container");
    expect(":iframe .o_header_mobile .o_main_nav").toHaveClass("container");
    await runAllTimers();
    expect.verifySteps([]);
});
