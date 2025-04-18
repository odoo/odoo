import {
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
    clickOnSnippet,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";

const SUB_SNIPPET_TEMPLATES = {
    s_masonry_block_default_template: "s_masonry_block",
    s_masonry_block_reversed_template: "s_masonry_block",
    s_masonry_block_images_template: "s_masonry_block",
    s_masonry_block_mosaic_template: "s_masonry_block",
    s_masonry_block_alternation_text_image_template: "s_masonry_block",
    s_masonry_block_alternation_image_text_template: "s_masonry_block",
};

const SNIPPET_NAME_NORMALIZATIONS = {
    "Hr": "Separator",
    "Cta Badge": "CTA Badge",
    "Website Form": "Form",
    "Searchbar Input": "Search",
};

// Extract snippets names from URL parameters
function getSnippetsNames() {
    let snippetsNamesRaw = new URL(document.location.href).searchParams.get("snippets_names") || "";
    const nestedPath = new URLSearchParams(window.location.search).get("path");
    if (nestedPath) {
        const splitPath = nestedPath.split("/");
        if (splitPath.length > 1) {
            const nestedSearch = new URLSearchParams(splitPath[1]);
            snippetsNamesRaw = nestedSearch.get("snippets_names") || snippetsNamesRaw;
        }
    }
    return snippetsNamesRaw
        .split(",")
        .map((snippet) => snippet.trim())
        .filter((snippet) => snippet); // Remove empty strings
}

// Generate steps for each snippet
function generateSnippetSteps(snippetsNames) {
    let steps = [];
    let n = 0;
    for (const snippet of snippetsNames) {
        n++;
        const snippetData = {
            name: snippet.split(":")[0],
            group: snippet.split(":")[1],
        };
        const isModal = ["s_popup", "s_newsletter_subscribe_popup"].includes(snippetData.name);

        const searchSnippetName = snippetData.name
            .split("_")
            .slice(1)
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
        const snippetKey = SUB_SNIPPET_TEMPLATES[snippetData.name] || snippetData.name;

        let draggableElSelector = "";
        if (snippetData.group) {
            draggableElSelector = `.o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[data-snippet-group="${snippetData.group}"] .o_snippet_thumbnail`;
        } else {
            const normalizedSnippetName =
                SNIPPET_NAME_NORMALIZATIONS[searchSnippetName] || searchSnippetName;
            draggableElSelector = `.o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) #snippet_content .o_snippet[name="${normalizedSnippetName}"] .o_snippet_thumbnail`;
        }

        const snippetSteps = [
            {
                content: `Drop ${snippetData.group || snippetData.name} ${
                    snippetData.group ? "group" : "snippet"
                } [${n}/${snippetsNames.length}]`,
                trigger: draggableElSelector,
                run: "drag_and_drop :iframe #wrap .oe_drop_zone",
            },
            {
                content: `Click on ${snippetData.name} snippet`,
                trigger: `:iframe #wrapwrap [data-snippet="${snippetKey}"]`,
                run: "click",
            },
            {
                content: `Check ${snippetData.name} settings are loaded, wait panel is visible`,
                trigger: ".o_customize_tab",
            },
            {
                content: `Remove the ${snippetData.name} snippet`,
                trigger: ".options-container .oe_snippet_remove:last",
                run: "click",
            },
            goBackToBlocks(),
        ];

        if (snippetData.group) {
            snippetSteps.splice(1, 0, {
                content: "Click on the snippet preview in the dialog",
                trigger: `:iframe .o_snippet_preview_wrap[data-snippet-id="${snippetData.name}"]`,
                run: "click",
            });
        }

        if (snippetData.name === "s_popup") {
            snippetSteps.splice(2, 1, {
                content: "Click on the s_popup snippet",
                trigger: ":iframe .s_popup .modal",
                run: "click",
            });
        }

        if (snippetData.name === "s_google_map") {
            snippetSteps.splice(2, 4, {
                content: "Close API Key popup",
                trigger: ":iframe .modal-footer .btn-secondary",
                run: "click",
            });
        } else if (isModal) {
            snippetSteps.splice(
                4,
                3,
                {
                    content: `Hide the ${snippetData.name} popup`,
                    trigger: `:iframe [data-snippet="${snippetData.name}"] .s_popup_close`,
                    run: "click",
                },
                {
                    content: `Make sure ${snippetData.name} is hidden`,
                    trigger: ":iframe body:not(.modal-open)",
                }
            );
        } else if (["s_button", "s_video"].includes(snippetData.name)) {
            snippetSteps[1].trigger =
                snippetData.name === "s_button"
                    ? `:iframe #wrapwrap .s_text_image .btn`
                    : `:iframe #wrapwrap .s_text_image .media_iframe_video`;
        }

        steps = steps.concat(snippetSteps);
    }
    return steps;
}

// Main execution
const snippetsNames = getSnippetsNames();
const steps = generateSnippetSteps(snippetsNames);

registerWebsitePreviewTour(
    "snippets_all_drag_and_drop",
    {
        url: `/?enable_editor=1&snippets_names=${snippetsNames.join(",")}`,
        edition: true,
    },
    () =>
        [
            {
                content: "Ensure snippets are actually passed at the test.",
                trigger: "body",
                run: function () {
                    if (steps.length < 500) {
                        console.error(
                            `This test is not behaving as it should, got only ${steps.length} steps.`
                        );
                    }
                },
            },
            ...insertSnippet({ id: "s_text_image", name: "Text - Image", groupName: "Content" }),
            ...clickOnSnippet({ id: "s_text_image", name: "Text - Image" }),
            {
                content: "Check settings are loaded, wait panel is visible",
                trigger: ".o_customize_tab [data-container-title='Text - Image']",
            },
            ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
            ...changeOptionInPopover("Header", "Header Position", "Hidden"),
            goBackToBlocks(),
        ].concat(steps)
);
