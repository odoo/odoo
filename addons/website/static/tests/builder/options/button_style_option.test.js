import {
    animationFrame,
    describe,
    expect,
    queryFirst,
    queryOne,
    test,
    getFixture,
} from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { delay } from "@web/core/utils/concurrency";

describe.current.tags("desktop");
defineWebsiteModels();

test("fill color preview shows the hover fill color in outline mode", async () => {
    await setupWebsiteBuilder(
        '<p><a href="https://test.com/" class="btn btn-outline-custom" >Link label</a></p>',
        { loadIframeBundles: true }
    );
    await contains(":iframe p > a").click();

    // Set a background color
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#0000FF']").click();

    expect(":iframe p > a").toHaveStyle(
        "background-color: rgba(0, 0, 0, 0); background-image: none",
        {
            message:
                "When not hovering, the button background should be transparent in outline mode",
        }
    );
    expect(":iframe p > a").toHaveStyle("background-color: rgb(0, 0, 255)", { inline: true });
    expect("[data-label=Fill] .o_we_color_preview").toHaveStyle(
        "background-color: rgb(0, 0, 255)",
        { inline: true, message: "The fill color preview should show the hover fill color" }
    );

    // Set a background gradient
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".gradient-tab").click();
    const gradientButton = queryFirst(".o_gradient_color_button");
    const gradient = gradientButton.dataset.color;
    await contains(gradientButton).click();

    expect(":iframe p > a").toHaveStyle(
        "background-color: rgba(0, 0, 0, 0); background-image: none",
        {
            message:
                "When not hovering, the button background should be transparent in outline mode",
        }
    );
    expect(":iframe p > a").toHaveStyle({ "background-image": gradient }, { inline: true });
    expect("[data-label=Fill] .o_we_color_preview").toHaveStyle(
        { "background-image": gradient },
        { inline: true, message: "The fill color preview should show the hover fill color" }
    );
});

test("keep current style when switching from button", async () => {
    await setupWebsiteBuilder('<p><a href="#" class="btn btn-secondary">Button Secondary</a></p>', {
        loadIframeBundles: true,
    });

    const computedStyle = getComputedStyle(queryOne(":iframe p > a"));
    const buttonSecondaryStyles = {
        "background-color": computedStyle.backgroundColor,
        border: computedStyle.border,
        color: computedStyle.color,
    };
    await contains(":iframe p > a").click();

    expect("[data-label=Type] .o-hb-select-toggle").toHaveText("Button Secondary");
    await contains("[data-label=Type] .o-hb-select-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    expect(":iframe p > a").toHaveClass("btn btn-custom");
    expect(":iframe p > a").toHaveStyle(buttonSecondaryStyles, { inline: true });
});

test("should preview button styles in dropdown", async () => {
    await setupWebsiteBuilder(
        `<p>
            <a href="#" class="btn btn-primary test-target">clickme</a>
            <a href="#" class="btn btn-secondary test-target">clickme</a>
        </p>`,
        {
            loadIframeBundles: true,
        }
    );

    await contains(":iframe p > a.test-target").click();
    // primary count=2 because it's shown both in dropdown list and trigger
    expect(".o-hb-button-style-preview.btn-primary").toHaveCount(2);
    expect(".o-hb-button-style-preview.btn-secondary").toHaveCount(1);
    expect(".o-hb-button-style-preview.btn-custom").toHaveCount(1);

    const primaryStyle = getComputedStyle(queryOne(":iframe .btn-primary.test-target"));
    const secondaryStyle = getComputedStyle(queryOne(":iframe .btn-secondary.test-target"));
    const previewVariables = [
        "background-color",
        "border-color",
        "border-style",
        "color",
        "font-family",
        "font-weight",
        "text-transform",
    ];

    previewVariables.forEach((v) => {
        expect(".o-hb-button-style-preview.btn-primary").toHaveStyle(`${v}: ${primaryStyle[v]}`);
        expect(".o-hb-button-style-preview.btn-secondary").toHaveStyle(
            `${v}: ${secondaryStyle[v]}`
        );
    });
});

test("should have a button linking to theme tab", async () => {
    await setupWebsiteBuilder(
        `<p>
            <a href="#" class="btn btn-custom test-target">clickme</a>
        </p>`,
        {
            loadIframeBundles: true,
        }
    );
    const fixture = getFixture();
    fixture.classList.add("allow-transitions");

    await contains(":iframe p > a.test-target").click();
    await contains("a.o-hb-theme-tab-link").click();

    // Fade out
    await delay(180);
    await animationFrame();
    expect("button[data-name='customize']").toHaveClass("active");
    expect("button[data-name='theme']").not.toHaveClass("active");

    // Theme tab is loaded
    await delay(200);
    await animationFrame();
    expect("button[data-name='customize']").not.toHaveClass("active");
    expect("button[data-name='theme']").toHaveClass("active");

    fixture.classList.remove("allow-transitions");
});

test("button border width is not previewed", async () => {
    await setupWebsiteBuilder(
        `<p>
            <a href="#" class="btn btn-custom test-target">clickme</a>
        </p>`,
        {
            loadIframeBundles: true,
        }
    );

    await contains(":iframe p > a.test-target").click();
    await contains("[data-label='Border'] .o_we_color_preview").click();
    await contains("button[data-color='#000000']").click();
    await contains(".options-container [data-label=Border] input").edit("3", {
        confirm: "enter",
    });
    // If border width is > 0, previewed width is fixed to 2 px
    expect(".options-container .o-hb-select-toggle .o-hb-button-style-preview").toHaveStyle({
        "border-width": "2px",
    });

    await contains(".options-container [data-label=Border] input").edit("0", {
        confirm: "enter",
    });
    // If border width is 0, previewed width is 0
    expect(".options-container .o-hb-select-toggle .o-hb-button-style-preview").toHaveStyle({
        "border-color": "rgba(0, 0, 0, 0)",
    });
});
