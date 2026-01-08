import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

describe.current.tags("desktop");

function getShapeTestCSS() {
    return `
        /* CSS Variables for theme colors */
        :root {
            --o-color-1: #3aadaa;
            --o-color-2: #7c6576;
            --o-color-3: #dd7777;
            --o-color-4: #383e45;
            --o-color-5: #f0f0f0;
            --o-cc1-bg: #3aadaa;
            --o-cc2-bg: #7c6576;
            --o-cc3-bg: #dd7777;
            --o-cc4-bg: #383e45;
            --o-cc5-bg: #f0f0f0;
        }
        
        body {
            margin: 0;
        }
        /* Base shape styles - required for positioning and layout */
        .o_we_shape {
            position: absolute !important;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            display: block;
            overflow: hidden;
            pointer-events: none;
        }
        /* Connections shapes */
        .o_we_shape.o_html_builder_Connections_01 {
            background-image: url("/html_editor/shape/html_builder/Connections/01.svg?c5=%23383e45");
            background-position: 50% 100%;
            background-size: 100% auto;
            background-repeat: no-repeat;
        }
        .o_we_shape.o_html_builder_Connections_02 {
            background-image: url("/html_editor/shape/html_builder/Connections/02.svg?c5=%23383e45");
            background-position: 50% 100%;
            background-size: 100% auto;
            background-repeat: no-repeat;
        }
    `;
}

test("Connections shape updates when header color changes", async () => {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {}
    }
    defineWebsiteModels();
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", async (request) => "");
    await setupWebsiteBuilder(
        `
        <main>
            <section id="section1" style="background-color: rgb(0, 0, 255);"'>
                <div class="container">
                    Section 1
                </div>
            </section>
        </main>
    `,
        {
            headerContent: `<header id="top" data-anchor="true" data-name="Header" style="background-color: rgb(255, 0, 0);">
                <div class="container">
                    <nav>Header Content</nav>
                </div>
            </header>`,
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section1").click();
    await contains("[data-label='Shape'] button").click();
    await animationFrame();
    await contains(
        "button[data-action-id='setBackgroundShape'][data-action-value='html_builder/Connections/01']"
    ).click();
    await animationFrame();
    await contains("[data-action-param='y']").click();
    await animationFrame();
    const ShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(ShapeData.colors.c5).toBe("#ff0000");
    await animationFrame();
    await contains(":iframe header").click();
    await animationFrame();
    await contains("[data-label='Background'] .o_we_color_preview").click();
    await contains("[data-color='o_cc3']").click();
    await animationFrame();
    const updatedShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(updatedShapeData.colors.c5).toBe("#dd7777");
});
