import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { queryFirst } from "@odoo/hoot-dom";
import { unfoldAllOptionsGroups } from "@html_builder/../tests/helpers";

defineWebsiteModels();

const carouselStyle = `
    .slide:not(.carousel-instant) {
        --transition-duration: 600ms;
        .carousel-item {
            transition-duration: var(--transition-duration) !important;
        }
    }

    .carousel-instant {
        .carousel-item {
            transition: none;
        }
    }
`;

test("Test Carousel Option (s_carousel)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel", {
        styleContent: carouselStyle,
    });
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    // Editing the Autoplay

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    // Editing the Timespan

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3600");

    await contains(".o_hb_row[data-label='Timespan'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Speed

    expect(carouselEl).not.toHaveStyle("--transition-duration", { inline: true });
    expect(carouselEl).toHaveStyle({ "--transition-duration": "600ms" });

    await contains(".o_hb_row[data-label='Duration'] input[type='number']").edit("2");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    // Autoplay: Never doesn't remove bs-interval

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });
});

test("Test Carousel Option (s_image_gallery)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_image_gallery", {
        styleContent: carouselStyle,
    });
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Autoplay

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Timespan

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3600");

    await contains(".o_hb_row[data-label='Timespan'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Speed

    expect(carouselEl).not.toHaveStyle("--transition-duration", { inline: true });
    expect(carouselEl).toHaveStyle({ "--transition-duration": "600ms" });

    await contains(".o_hb_row[data-label='Duration'] input[type='number']").edit("2");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    // Autoplay: Never doesn't remove bs-interval

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });
});

test("Test carousel item height matches configured section height", async () => {
    await setupWebsiteBuilderWithSnippet("s_carousel", { loadIframeBundles: true });
    await contains(":iframe .s_carousel").click();

    const carouselItemEl = queryFirst(":iframe .carousel-item");
    const iframeHeight = carouselItemEl.ownerDocument.defaultView.innerHeight;

    await contains("button[data-action-param='o_full_screen_height']").click();
    expect(carouselItemEl.getBoundingClientRect().height).toBeCloseTo(iframeHeight, {
        margin: 1,
    });

    await contains("button[data-action-param='o_three_quarter_height']").click();
    expect(carouselItemEl.getBoundingClientRect().height).toBeCloseTo(iframeHeight * 0.75, {
        margin: 1,
    });
});

/**
 * Returns the controllers of the given container in DOM order, so that it
 * can be compared to their visual order.
 *
 * @param {HTMLElement} containerEl
 * @returns {string[]}
 */
function getControllersOrder(containerEl) {
    const controllers = {
        o_carousel_pause: "pause",
        "carousel-control-prev": "prev",
        "carousel-control-next": "next",
        "carousel-indicators": "indicators",
        o_arrows_wrapper: "arrows",
    };
    return [...containerEl.children]
        .map((el) => Object.entries(controllers).find(([cls]) => el.classList.contains(cls))?.[1])
        .filter(Boolean);
}

/**
 * Opens the select of the given option row and clicks on the given item.
 *
 * @param {string} rowLabel
 * @param {string} itemLabel
 */
async function selectOption(rowLabel, itemLabel) {
    await contains(`.o_hb_row[data-label='${rowLabel}'] button`).click();
    await contains(`.o_hb_select_dropdown_item:contains('${itemLabel}')`).click();
}

test("Carousel controllers DOM order follows the 'Control' option (s_carousel_intro)", async () => {
    const { getEditor, getEditableContent, waitSidebarUpdated } =
        await setupWebsiteBuilderWithSnippet("s_carousel_intro", { loadIframeBundles: true });
    const rowEl = getEditableContent().querySelector(".o_horizontal_controllers_row");
    // Reproduce the legacy layout using `flex-row-reverse`.
    rowEl.prepend(rowEl.querySelector(":scope > .o_arrows_wrapper"));
    rowEl.classList.add("flex-row-reverse");
    getEditor().shared.history.commit();

    await contains(":iframe .s_carousel_intro .carousel-item.active").click();
    await waitSidebarUpdated();
    await unfoldAllOptionsGroups();
    // Visually, the indicators are first: it is the default layout.
    expect(".o_hb_row[data-label='Control'] button").toHaveText("Default");

    // Reversed: the class is removed and the arrows are first in the DOM.
    await selectOption("Control", "Reversed");
    expect(rowEl).not.toHaveClass("flex-row-reverse");
    expect(getControllersOrder(rowEl)).toEqual(["arrows", "indicators"]);
    expect(".o_hb_row[data-label='Control'] button").toHaveText("Reversed");

    // Default: the indicators are first in the DOM.
    await selectOption("Control", "Default");
    expect(getControllersOrder(rowEl)).toEqual(["indicators", "arrows"]);
    expect(".o_hb_row[data-label='Control'] button").toHaveText("Default");

    // Undo restores the previous markup.
    getEditor().shared.history.undo();
    await waitSidebarUpdated();
    expect(getControllersOrder(rowEl)).toEqual(["arrows", "indicators"]);
    expect(".o_hb_row[data-label='Control'] button").toHaveText("Reversed");

    // Centered (only available when a controller is hidden) keeps the order.
    await selectOption("Indicators", "Hidden");
    await selectOption("Control", "Centered");
    expect(rowEl).toHaveClass("justify-content-center");
    expect(rowEl).not.toHaveClass("justify-content-between");
    expect(getControllersOrder(rowEl)).toEqual(["arrows", "indicators"]);
});

test("Carousel controllers DOM order follows the 'Control' option (s_image_gallery)", async () => {
    const { getEditor, getEditableContent, waitSidebarUpdated } =
        await setupWebsiteBuilderWithSnippet("s_image_gallery", {
            loadIframeBundles: true,
            loadIframeBuilderTemplates: true,
        });
    const getOrder = () =>
        getControllersOrder(getEditableContent().querySelector(".o_carousel_controllers"));
    // Default: "Outside, at left".
    expect(getOrder()).toEqual(["pause", "indicators", "prev", "next"]);

    await contains(":iframe .s_image_gallery").click();
    await waitSidebarUpdated();
    await unfoldAllOptionsGroups();

    await selectOption("Control", "Outside, center");
    expect(getOrder()).toEqual(["pause", "prev", "indicators", "next"]);

    await selectOption("Control", "Outside, at right");
    expect(getOrder()).toEqual(["pause", "prev", "next", "indicators"]);

    await selectOption("Control", "Classic");
    expect(getOrder()).toEqual(["prev", "next", "pause", "indicators"]);

    getEditor().shared.history.undo();
    await waitSidebarUpdated();
    expect(getOrder()).toEqual(["pause", "prev", "next", "indicators"]);

    await contains("[data-action-id='removeAllImages']").click();
    expect(getOrder()).toEqual(["pause", "prev", "next", "indicators"]);
});
