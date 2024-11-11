import {
    clickOnEditAndWaitEditMode,
    insertSnippet,
    goBackToBlocks,
    clickOnSnippet,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";
import { registry } from "@web/core/registry";

export const SUB_SNIPPET_TEMPLATES = {
    s_masonry_block_default_template: "s_masonry_block",
    s_masonry_block_reversed_template: "s_masonry_block",
    s_masonry_block_images_template: "s_masonry_block",
    s_masonry_block_mosaic_template: "s_masonry_block",
    s_masonry_block_alternation_text_image_template: "s_masonry_block",
    s_masonry_block_alternation_image_text_template: "s_masonry_block",
};

const DROP_IN_ONLY_SNIPPETS = {
    "s_button": ".btn",
    "s_video": ".media_iframe_video",
};

// Extract the snippets names from the URL parameters.
let snippetsNames = (new URL(document.location.href)).searchParams.get("snippets_names") || "";
// When this test is loaded in the backend, the search params aren't as easy to
// read as before. Little trickery to make this test run.
const searchParams = new URLSearchParams(window.location.search).get("path");
if (searchParams) {
    snippetsNames = new URLSearchParams(searchParams.split("/")[1]).get("snippets_names") || "";
    snippetsNames = snippetsNames.split(",");
}

registry.category("web_tour.tours").add("snippets_all_drag_and_drop", {
    steps: () => {
        let steps = [];
        let n = 0;
        // Generate the tour steps for each snippet.
        for (let snippet of snippetsNames) {
            n++;
            snippet = {
                name: snippet.split(":")[0],
                group: snippet.split(":")[1],
            };
            const isModal = ["s_popup", "s_newsletter_subscribe_popup", "s_newsletter_benefits_popup"].includes(snippet.name);
            const isDropInOnlySnippet = Object.keys(DROP_IN_ONLY_SNIPPETS).includes(snippet.name);
            const snippetKey = SUB_SNIPPET_TEMPLATES[snippet.name] || snippet.name;

            let draggableElSelector = "";
            if (snippet.group) {
                draggableElSelector = `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups [data-snippet-group="${snippet.group}"] .o_snippet_thumbnail`;
            } else {
                draggableElSelector = `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_content [data-snippet="${snippet.name}"].o_snippet_thumbnail`;
            }

            const snippetSteps = [
                {
                    content: `Drop ${snippet.group || snippet.name} ${snippet.group ? "group" : "snippet"} [${n}/${snippetsNames.length}]`,
                    trigger: draggableElSelector,
                    run: "drag_and_drop :iframe #wrapwrap .oe_drop_zone",
                },
                {
                    content: "Wait for the drag and drop to be over", // TODO find a better way
                    trigger: ".o_block_tab:not(.o_we_ongoing_insertion)",
                },
                {
                    content: `Click on ${snippet.name} snippet`,
                    trigger: `:iframe #wrapwrap [data-snippet="${snippetKey}"]${isModal ? " .modal.show" : ""}`,
                    run: "click",
                },
                {
                    content: `Check ${snippet.name} settings are loaded, wait for panel to be visible`,
                    trigger: ".o_customize_tab",
                },
                {
                    content: `Remove the ${snippet.name} snippet`, // Avoid bad perf if many snippets
                    trigger: ".options-container .oe_snippet_remove:last",
                    run: "click",
                },
                goBackToBlocks(),
            ];

            if (snippet.group) {
                snippetSteps.splice(1, 0, {
                    content: "Click on the snippet preview in the dialog",
                    trigger: `:iframe .o_snippet_preview_wrap[data-snippet-id="${snippet.name}"]`,
                    run: "click",
                });
            }

            if (snippet.name === "s_google_map") {
                snippetSteps.splice(3, 3, {
                    content: "Close API Key popup",
                    trigger: ":iframe .modal-footer .btn-secondary",
                    run: "click",
                });
            } else if (isModal) {
                snippetSteps.splice(5, 2, {
                    content: `Make sure ${snippet.name} is shown`,
                    trigger: ":iframe body.modal-open",
                }, {
                    content: `Hide the ${snippet.name} popup`,
                    trigger: `:iframe [data-snippet='${snippet.name}'] .s_popup_close`,
                    run: "click",
                });
            } else if (isDropInOnlySnippet) {
                // The 'drop in only' snippets have their 'data-snippet' attribute
                // removed once they are dropped, so we need to use a different
                // selector.
                snippetSteps[2].trigger = `:iframe #wrapwrap ${DROP_IN_ONLY_SNIPPETS[snippet.name]}`;
            }
            steps = steps.concat(snippetSteps);
        }

        return [
            // To run the tour locally, you need to insert the URL sent by the python
            // tour here. There is currently an issue with tours which don't have an URL
            // url: '/?enable_editor=1&snippets_names=s_process_steps:columns,s_website_form:,s_...',
            ...clickOnEditAndWaitEditMode(),
            {
                content: "Ensure snippets are actually passed at the test.",
                trigger: "body",
                run: function () {
                    // Safety check, otherwise the test might "break" one day and
                    // receive no steps. The test would then not test anything anymore
                    // without us noticing it.
                    if (steps.length < 500) {
                        console.error(`This test is not behaving as it should, got only ${steps.length} steps.`);
                    }
                },
            },
            // This first step is needed as it will be used later for inner snippets.
            // Without this, it will dropped inside the footer and will need an extra
            // selector.
            ...insertSnippet({ id: "s_text_image", name: "Text - Image", groupName: "Content" }),
            {
                content: "Click on s_text_image snippet",
                trigger: ":iframe #wrap.o_editable [data-snippet='s_text_image']",
                run: "click",
            },
            {
                content: "Check settings are loaded, wait for panel to be visible",
                trigger: ".o_customize_tab [data-container-title='Text - Image']",
            },
            // We hide the header before starting to drop snippets. This prevents
            // situations where the header's drop zones overlap with those of the #wrap,
            // ensuring that a snippet is dropped in the #wrap as expected instead of
            // the header.
            ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
            ...changeOptionInPopover("Header", "Header Position", "Hidden"),
            goBackToBlocks(),
        ].concat(steps).map((step) => {
            delete step.noPrepend;
            return step;
        });
    },
});
