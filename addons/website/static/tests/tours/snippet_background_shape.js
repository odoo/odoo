import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    goBackToBlocks,
    clickOnElement,
} from "@website/js/tours/tour_utils";
import { rgbToHex } from "@web/core/utils/colors";

function assertSnippetBgAndShapeBgEqual(snippetEl, shapeSnippetEl) {
    const shapeEl = shapeSnippetEl.querySelector(".o_we_shape");
    const shapeBackgroundImage = window
        .getComputedStyle(shapeEl)
        .getPropertyValue("background-image");
    const urlMatch = shapeBackgroundImage.match(/url\(["']?(.*?)["']?\)/);
    const url = urlMatch[1];
    const urlParams = new URLSearchParams(url.split("?")[1]);
    let shapeColor = undefined;
    for (const [key, value] of urlParams.entries()) {
        if (/^c[1-5]$/.test(key)) {
            shapeColor = value;
        }
    }
    return rgbToHex(getComputedStyle(snippetEl).backgroundColor) == shapeColor;
}

registerWebsitePreviewTour(
    "snippet_background_shape_color",
    {
        edition: true,
        url: "/",
    },
    () => [
        ...insertSnippet({
            id: "s_three_columns",
            name: "Three Columns",
            groupName: "Columns",
        }),
        ...insertSnippet({
            id: "s_three_columns",
            name: "Three Columns",
            groupName: "Columns",
        }),
        {
            content: "Edit the first snippet",
            trigger: ":iframe #wrap.o_editable .s_three_columns",
            run: "click",
        },
        {
            content: "Add a background shape",
            trigger: "we-button[title=Shape]",
            run: "click",
        },
        {
            content: "validate the shape",
            trigger: ":iframe #wrap.o_editable .s_three_columns",
            run: "click",
        },
        {
            content: `Check that the shape has a different color`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const snippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns");
                if (assertSnippetBgAndShapeBgEqual(snippetEl, snippetEl)) {
                    throw new Error(
                        "When two snippet have the same bg-color, the bg-color of the shape must be different"
                    );
                }
            },
        },
        {
            content: "Flip the background shape",
            trigger: "we-button[data-flip-y=true]",
            run: "click",
        },
        {
            content: `Check that the shapes has the same color than the header`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const headerEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector("header");
                const snippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns");
                if (!assertSnippetBgAndShapeBgEqual(headerEl, snippetEl)) {
                    throw new Error(
                        "When the shape is set just after the header it must take its bg-color"
                    );
                }
            },
        },
        {
            content: "Edit the second snippet",
            trigger: ":iframe #wrap.o_editable .s_three_columns:last-child",
            run: "click",
        },
        {
            content: "Edit the background color of the second snippet",
            trigger: "span[class=o_we_color_preview]",
            run: "click",
        },
        {
            content: "Select the 4th color",
            trigger: "button[data-color='4']",
            run: "click",
        },
        {
            content: "Add a background shape to the second snippet",
            trigger: "we-button[title=Shape]",
            run: "click",
        },
        {
            content: `Check that the shape color is the same as the footer background`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const footerEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector("footer");
                const snippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns:last-child");
                if (!assertSnippetBgAndShapeBgEqual(footerEl, snippetEl)) {
                    throw new Error(
                        "When the shape is set just before the footer it must take its bg-color"
                    );
                }
            },
        },
        {
            content: "Edit the first snippet",
            trigger: ":iframe #wrap.o_editable .s_three_columns",
            run: "click",
        },
        {
            content: "Flip the background shape",
            trigger: "we-button[data-flip-y=true]",
            run: "click",
        },
        {
            content: `Check that the color is the same as the following snippet`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const nextSnippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns:last-child");
                const snippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns");
                if (!assertSnippetBgAndShapeBgEqual(nextSnippetEl, snippetEl)) {
                    throw new Error(
                        "The bg-color of the shape must be the same as the next/previous snippet when the shape is flipped"
                    );
                }
            },
        },
        {
            content: "Edit the second snippet",
            trigger: ":iframe #wrap.o_editable .s_three_columns:last-child",
            run: "click",
        },
        {
            content: "Edit the background color of the second snippet",
            trigger: "span[class=o_we_color_preview]",
            run: "click",
        },
        {
            content: "Select the 4th color",
            trigger: "button[data-color='4']",
            run: "click",
        },
        {
            content: `Check that the color of the shape stays the same as the bg color of the snippet`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const nextSnippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns:last-child");
                const snippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns");
                if (!assertSnippetBgAndShapeBgEqual(nextSnippetEl, snippetEl)) {
                    throw new Error(
                        "The bg-color of the shape must be the same as the next/previous snippet when that snippet bg-color change"
                    );
                }
            },
        },
        goBackToBlocks(),
        ...insertSnippet({
            id: "s_three_columns",
            name: "Three Columns",
            groupName: "Columns",
        }),
        {
            content: `Check that the color of the shape of the previous snippet changed to match the bg-color of the added snippet`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const SnippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns:last-child");
                const previousSnippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns:nth-last-child(2)");
                if (!assertSnippetBgAndShapeBgEqual(SnippetEl, previousSnippetEl)) {
                    throw new Error(
                        "The bg-color of the shape must be the same as the next/previous snippet when a snippet is added"
                    );
                }
            },
        },
        {
            content: "Select last snippet",
            trigger: ":iframe #wrap.o_editable .s_three_columns:last-child",
            run: "click",
        },
        clickOnElement("trash button", ":iframe button.oe_snippet_remove"),
        {
            content: `Check that the shape color is the same as the footer background`,
            trigger: ":iframe #wrap.o_editable",
            run() {
                const footerEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector("footer");
                const snippetEl = document
                    .querySelector("iframe")
                    .contentDocument.body.querySelector(".s_three_columns:last-child");
                if (!assertSnippetBgAndShapeBgEqual(footerEl, snippetEl)) {
                    throw new Error(
                        "When the shape is set just before the footer it must take its bg-color"
                    );
                }
            },
        },
        ...clickOnSave(),
    ]
);
