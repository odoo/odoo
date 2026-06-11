import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { isHeaderBgBlurAvailable } from "@website/builder/plugins/options/header/header_template_option";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const headerContent = `
    <header id="top" data-anchor="true" data-name="Header">
        <nav class="navbar">Menu Content</nav>
    </header>`;

test("header blur option is only available when the background is not fully opaque", async () => {
    await setupWebsiteBuilder("", { openEditor: false, headerContent });
    const headerEl = queryOne(":iframe #wrapwrap > header");
    const navEl = headerEl.querySelector("nav");
    // The blur is applied on the nav, so only its background is relevant.
    const expectBlur = (navStyle) => {
        navEl.setAttribute("style", navStyle);
        return expect(isHeaderBgBlurAvailable(headerEl));
    };

    expectBlur("").toBe(true);

    expectBlur("--menu-custom: rgb(255, 0, 0)").toBe(false);
    expectBlur("--menu-custom: #ff0000").toBe(false);
    expectBlur("--menu-custom: #ff0000ff").toBe(false);
    expectBlur("--menu-custom: rgba(255, 0, 0, 0.5)").toBe(true);
    expectBlur("--menu-custom: #ff000080").toBe(true);

    expectBlur("--menu: 3; --o-cc3-bg: rgb(255, 0, 0)").toBe(false);
    expectBlur("--menu: 3; --o-cc3-bg: rgba(255, 0, 0, 0.5)").toBe(true);

    expectBlur("--menu-custom: rgba(255, 0, 0, 0.5); --menu-gradient: none").toBe(true);
    expectBlur("--menu-gradient: linear-gradient(rgba(255,0,0,0.5), blue)").toBe(true);
    expectBlur("--menu-gradient: linear-gradient(rgba(0,0,0,0.5), rgba(255,255,255,1))").toBe(true);
    expectBlur("--menu-gradient: linear-gradient(#ff000080, #0000ffff)").toBe(true);
    expectBlur("--menu-gradient: linear-gradient(#ff0000, #0000ff)").toBe(false);
    expectBlur("--menu: 3; --o-cc3-bg-gradient: linear-gradient(#ff000080, #0000ffff)").toBe(true);

    expectBlur("--menu-custom: #ff000080; --menu-gradient: linear-gradient(#ff0000, #0000ff)").toBe(
        false
    );
});

test("the blur option is hidden for an opaque header background", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder("", {
        openEditor: true,
        headerContent,
        styleContent: `#wrapwrap > header nav { --menu-custom: rgb(255, 0, 0); }`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await waitSidebarUpdated();
    expect("[data-label='Blur']").not.toHaveCount();
});

test("the blur option is shown for a transparent header background", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder("", {
        openEditor: true,
        headerContent,
        styleContent: `#wrapwrap > header nav { --menu-custom: rgba(255, 0, 0, 0.5); }`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await waitSidebarUpdated();
    expect("[data-label='Blur']").toBeVisible();
});
