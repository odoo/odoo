import { expect, queryFirst, test } from "@odoo/hoot";
import { waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getIframeInput } from "@html_editor/../tests/_helpers/iframe_input";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    PALETTE_URL as PALETTE,
    saveWebsite as save,
    setupWebsiteBuilder,
    USER_VALUES_URL as USER_VALUES,
} from "../website_helpers";

defineWebsiteModels();

// A page breadcrumb (its color preset is compiled in).
async function setupBreadcrumb(styleContent = ":root { --breadcrumb: 1; }") {
    await setupWebsiteBuilder("", {
        styleContent,
        onIframeLoaded: (iframe) => {
            const doc = iframe.contentDocument;
            const main = doc.createElement("main");
            main.innerHTML = `<div class="o_page_breadcrumb" data-name="Breadcrumb">
                <nav>Breadcrumb</nav></div>`;
            doc.querySelector("#wrap").before(main);
        },
    });
    await contains(":iframe .o_page_breadcrumb").click();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
}

test("an area's color preset is previewed as its class, written on save", async () => {
    mockThemeRpcs();
    await setupBreadcrumb();
    await contains(".o_popover [data-color='o_cc3']").click();
    expect(":iframe .o_page_breadcrumb nav").toHaveClass("o_cc3");
    expect(":iframe .o_page_breadcrumb nav").toHaveAttribute("data-o-cc-area", "breadcrumb");
    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    expect(":iframe .o_page_breadcrumb nav").not.toHaveClass("o_cc3");
    expect(":iframe .o_page_breadcrumb nav").not.toHaveAttribute("data-o-cc-area");
    await contains(".o_hb_snippets_top_actions button[data-icon='redo']").click();
    expect(":iframe .o_page_breadcrumb nav").toHaveClass("o_cc3");
    expect.verifySteps([]);
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"breadcrumb-gradient":"NULL"}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"3"}`,
    ]);
});

test("hovering an area's color preset keeps the applied one selected", async () => {
    mockThemeRpcs({ stepComputedColors: true });
    await setupBreadcrumb();
    expect(".o_popover [data-color='o_cc1']").toHaveClass("selected");
    await contains(".o_popover [data-color='o_cc3']").hover();
    // The computed colors arrive while previewing, and update the options.
    await expect.waitForSteps(["computed colors"]);
    await animationFrame();
    expect(".o_popover [data-color='o_cc1']").toHaveClass("selected");
    expect(".o_popover [data-color='o_cc3']").not.toHaveClass("selected");
    // Back to the saved colors: nothing left to compute.
    await contains(".o_hb_snippets_top_actions").hover();
    await animationFrame();
    expect.verifySteps([]);
});

test("an area's custom color and gradient switch their rules on", async () => {
    mockThemeRpcs();
    await setupBreadcrumb();
    const gates = () => queryFirst(":iframe html").dataset.oThemeGates || "";
    await contains(".o_popover .custom-tab").click();
    const hexInputEl = await getIframeInput(
        ".o_font_color_selector .o_color_picker_inputs iframe.o_hex_iframe",
        "input[name='hex_input']"
    );
    await contains(hexInputEl).edit("#FF0000");
    expect(gates()).toInclude("breadcrumb-custom");
    expect(queryFirst(":iframe html").style.getPropertyValue("--breadcrumb-custom")).toBe(
        "#FF0000"
    );
    await contains(".o_popover .gradient-tab").click();
    await contains(".o_popover .o_colorpicker_sections .o_color_button").click();
    expect(gates()).toInclude("breadcrumb-gradient");
    expect(gates()).not.toInclude("breadcrumb-custom");
    expect.verifySteps([]);
});

test("resetting a saved area color previews it unset", async () => {
    mockThemeRpcs();
    await setupBreadcrumb(":root { --breadcrumb: 1; --breadcrumb-custom: #FF0000; }");
    const htmlEl = queryFirst(":iframe html");
    await contains(".o_popover .o_color_picker_reset").click();
    // Unset, as the compile leaves a null value: not the saved one.
    expect(htmlEl.style.getPropertyValue("--breadcrumb-custom")).toBe("initial");
    expect(getComputedStyle(htmlEl).getPropertyValue("--breadcrumb-custom")).toBe("");
    expect("[data-label='Background Color'] button.o_we_color_preview").not.toHaveAttribute(
        "style",
        /255, 0, 0/
    );
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"breadcrumb-gradient":"NULL"}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"NULL"}`,
    ]);
});

test("the portal cards' color preset is previewed as their class", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", {
        styleContent: ":root { --portal-card: 1; }",
        onIframeLoaded: (iframe) => {
            const main = iframe.contentDocument.createElement("main");
            main.innerHTML = `<div class="o_portal_index_card"><a href="#">Card</a></div>`;
            iframe.contentDocument.querySelector("#wrap").before(main);
        },
    });
    await contains(":iframe .o_portal_index_card > a").click();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
    await contains(".o_popover [data-color='o_cc4']").click();
    expect(":iframe .o_portal_index_card > a").toHaveClass("o_cc4");
    expect(":iframe .o_portal_index_card > a").toHaveAttribute("data-o-cc-area", "portal-card");
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"portal-gradient":"NULL"}`,
        `${PALETTE} {"portal-card-custom":"NULL","portal-card":"4"}`,
    ]);
});

test("resetting an area color previews no color, over the palette's", async () => {
    mockThemeRpcs();
    // The palette gives the area a preset and a custom color.
    await setupBreadcrumb(`:root {
        --breadcrumb: 3; --o-default-breadcrumb: 3;
        --breadcrumb-custom: #FF0000; --o-default-breadcrumb-custom: #FF0000;
    }`);
    const htmlEl = queryFirst(":iframe html");
    await contains(".o_popover .o_color_picker_reset").click();
    // Marked without a preset: the compiled one stops applying.
    expect(":iframe .o_page_breadcrumb nav").toHaveAttribute("data-o-cc-area", "breadcrumb");
    expect(queryFirst(":iframe .o_page_breadcrumb nav").className).not.toMatch(/o_cc\d/);
    expect(htmlEl.style.getPropertyValue("--breadcrumb-custom")).toBe("initial");
    expect(htmlEl.dataset.oThemeGates || "").not.toInclude("breadcrumb-custom");
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"breadcrumb-gradient":"NULL"}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"NULL"}`,
    ]);
});

test("a preset over the palette's custom color of an area turns that color off", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", {
        styleContent: `:root {
            --breadcrumb: 1;
            --breadcrumb-custom: rgba(0, 0, 0, 0.15); --o-default-breadcrumb-custom: rgba(0, 0, 0, 0.15);
        }`,
        onIframeLoaded: (iframe) => {
            const doc = iframe.contentDocument;
            doc.documentElement.dataset.oThemeGates = "breadcrumb-custom";
            const main = doc.createElement("main");
            main.innerHTML = `<div class="o_page_breadcrumb" data-name="Breadcrumb"><nav>Breadcrumb</nav></div>`;
            doc.querySelector("#wrap").before(main);
        },
    });
    await contains(":iframe .o_page_breadcrumb").click();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
    await contains(".o_popover [data-color='o_cc2']").hover();
    const htmlEl = queryFirst(":iframe html");
    expect(":iframe .o_page_breadcrumb nav").toHaveClass("o_cc2");
    expect(htmlEl.dataset.oThemeGates).not.toInclude("breadcrumb-custom");
    expect(htmlEl.style.getPropertyValue("--breadcrumb-custom")).toBe("initial");
    await contains(".o_hb_snippets_top_actions").hover();
    expect(htmlEl.dataset.oThemeGates).toInclude("breadcrumb-custom");
});

test("an area's color stays through a palette switch, which doesn't ask for it", async () => {
    mockThemeRpcs();
    await setupBreadcrumb(":root { --breadcrumb: 1; }");
    await contains(".o_popover [data-color='o_cc3']").click();
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
    await contains(".o_theme_tab [data-icon='palette']").click();
    await contains(`[data-action-value="'default-light-1'"] .o_hb_color_palette_card span`).click();
    expect(".o_dialog").toHaveCount(0);
    expect(":iframe .o_page_breadcrumb nav").toHaveClass("o_cc3");
    await save();
    expect.verifySteps([
        `${USER_VALUES} ${JSON.stringify({
            "breadcrumb-gradient": "NULL",
            "color-palettes-name": "'default-light-1'",
            ...Object.fromEntries([1, 2, 3, 4, 5].map((i) => [`o-cc${i}-bg-gradient`, "null"])),
        })}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"3"}`,
    ]);
});

test("the colors computed from an area's previewed color are the latest ones", async () => {
    mockThemeRpcs();
    const firstAnswer = Promise.withResolvers();
    onRpc("/website/theme_computed_colors", async (request) => {
        const { params } = await request.json();
        if (params.areas.breadcrumb === "2") {
            await firstAnswer.promise;
        }
        return { values: { "test-computed": params.areas.breadcrumb }, gates: {} };
    });
    await setupBreadcrumb();
    const htmlEl = queryFirst(":iframe html");
    await contains(".o_popover [data-color='o_cc2']").click();
    await animationFrame();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
    await contains(".o_popover [data-color='o_cc3']").click();
    await waitUntil(() => htmlEl.style.getPropertyValue("--test-computed") === "3");
    firstAnswer.resolve();
    await animationFrame();
    expect(htmlEl.style.getPropertyValue("--test-computed")).toBe("3");
});

test("the gates computed from the colors follow the previewed colors", async () => {
    mockThemeRpcs();
    onRpc("/website/theme_computed_colors", () => ({ values: {}, gates: { "menu-dark": true } }));
    await setupBreadcrumb();
    const htmlEl = queryFirst(":iframe html");
    await contains(".o_popover [data-color='o_cc5']").click();
    await waitUntil(() => htmlEl.dataset.oThemeGates?.includes("menu-dark"));
    // Nothing previewed: nothing computed.
    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    await waitUntil(() => !htmlEl.dataset.oThemeGates?.includes("menu-dark"));
});

test("an area's previewed preset isn't saved with the page", async () => {
    mockThemeRpcs();
    onRpc("ir.ui.view", "save", ({ args }) => {
        expect.step(
            args[1].includes("o-cc-area") || args[1].includes("o_cc4") ? "marked" : "clean"
        );
        return true;
    });
    const { getEditor } = await setupWebsiteBuilder(
        `<div class="o_portal_index_card"><a href="#">Card</a></div>`,
        { styleContent: ":root { --portal-card: 1; }" }
    );
    await contains(":iframe .o_portal_index_card > a").click();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
    await contains(".o_popover [data-color='o_cc4']").click();
    expect(":iframe .o_portal_index_card > a").toHaveAttribute("data-o-cc-area", "portal-card");
    // An edit of the page around it.
    queryFirst(":iframe .o_portal_index_card").append("Edited");
    getEditor().shared.history.commit();
    await save();
    expect.verifySteps([
        "clean",
        `${USER_VALUES} {"portal-gradient":"NULL"}`,
        `${PALETTE} {"portal-card-custom":"NULL","portal-card":"4"}`,
    ]);
});
