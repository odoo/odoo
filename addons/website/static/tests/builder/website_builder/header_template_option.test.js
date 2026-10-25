import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
defineWebsiteModels();

const headerContent = `
    <header id="top" data-anchor="true" data-name="Header" id="o_main_nav">
        <nav data-name="Navbar" class="navbar">
            <div id="o_main_nav" class="o_main_nav container"> content </div>
        </nav>
    </header>`;

test("width preview is disabled on incompatible templates", async () => {
    onRpc("/website/theme_customize_data_get", async () => [
        "website.header_navbar_pills_style",
        "website.template_header_boxed",
    ]);
    await setupWebsiteBuilder("", { headerContent });
    await contains(":iframe .o_main_nav").click();
    await waitFor("[data-label='Content Width']");
    expect("[data-label='Content Width'] [data-action-id='websiteConfig']").toHaveCount(3);
    expect("[data-label='Content Width'] [data-action-id='previewableWebsiteConfig']").toHaveCount(
        0
    );
});

test("width preview is enabled by default", async () => {
    await setupWebsiteBuilder("", { headerContent });
    await contains(":iframe .o_main_nav").click();
    await waitFor("[data-label='Content Width']");
    expect("[data-label='Content Width'] [data-action-id='previewableWebsiteConfig']").toHaveCount(
        3
    );
    expect("[data-label='Content Width'] [data-action-id='websiteConfig']").toHaveCount(0);
});
