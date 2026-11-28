import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { isHeaderBgBlurAvailable } from "@website/builder/plugins/options/header/header_template_option";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const headerContent = `
    <header id="top" data-anchor="true" data-name="Header">
        <nav class="navbar">
            <div id="o_main_nav" class="container o_main_nav"> content </div>
        </nav>
    </header>`;

describe("header blur option", () => {
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
        expectBlur("--menu-gradient: linear-gradient(rgba(0,0,0,0.5), rgba(255,255,255,1))").toBe(
            true
        );
        expectBlur("--menu-gradient: linear-gradient(#ff000080, #0000ffff)").toBe(true);
        expectBlur("--menu-gradient: linear-gradient(#ff0000, #0000ff)").toBe(false);
        expectBlur("--menu: 3; --o-cc3-bg-gradient: linear-gradient(#ff000080, #0000ffff)").toBe(
            true
        );

        expectBlur(
            "--menu-custom: #ff000080; --menu-gradient: linear-gradient(#ff0000, #0000ff)"
        ).toBe(false);
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
});

describe("header width option", () => {
    test("the width is previewed and applied on every element printing it", async () => {
        onRpc("/website/theme_customize_data", async (request) => {
            const { params } = await request.json();
            expect.step(`enable ${params.enable}`);
        });
        // Nested width elements (as in the Rounded Box layout), and the mobile
        // header's container, which doesn't follow the option.
        const { getEditor } = await setupWebsiteBuilder("", {
            headerContent: `
                <header id="top" data-anchor="true" data-name="Header">
                    <div class="container o_header_content_width test-outer">
                        <nav class="navbar">
                            <div id="o_main_nav" class="container o_header_content_width o_main_nav"> content </div>
                        </nav>
                    </div>
                    <nav class="o_header_mobile"><div class="container test-mobile"> mobile </div></nav>
                </header>`,
        });
        await contains(":iframe #wrapwrap > header").click();
        await contains("[data-label='Content Width'] button[title='Small']").hover();
        expect(":iframe .test-outer").toHaveClass("o_container_small");
        expect(":iframe #o_main_nav").toHaveClass("o_container_small");
        expect(":iframe #o_main_nav").not.toHaveClass("container");
        expect(":iframe .test-mobile").toHaveClass("container");
        expect(":iframe .test-mobile").not.toHaveClass("o_container_small");

        await contains("[data-label='Content Width'] button[title='Small']").click();
        await contains("[data-label='Content Width'] button[title='Full']").click();
        expect(":iframe .test-outer").toHaveClass("container-fluid");
        expect(":iframe #o_main_nav").toHaveClass("container-fluid");
        expect(":iframe .test-outer").not.toHaveClass("container");
        expect("[data-label='Content Width'] button[title='Full']").toHaveClass("active");

        // A click stages one operation per marked element: undo reverts them
        // all, the views to save included.
        undo(getEditor());
        await animationFrame();
        expect(":iframe .test-outer").toHaveClass("o_container_small");
        expect(":iframe #o_main_nav").toHaveClass("o_container_small");
        expect(":iframe #o_main_nav").not.toHaveClass("container-fluid");
        expect("[data-label='Content Width'] button[title='Small']").toHaveClass("active");

        redo(getEditor());
        await animationFrame();
        expect(":iframe .test-outer").toHaveClass("container-fluid");
        expect(":iframe #o_main_nav").toHaveClass("container-fluid");

        undo(getEditor());
        await contains(".o_hb_snippets_top_actions [data-action='save']").click();
        expect.verifySteps(["enable website.header_width_small"]);
    });
});
