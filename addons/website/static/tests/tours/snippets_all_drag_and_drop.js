/** @odoo-module **/

import {
    clickOnEditAndWaitEditMode,
    insertSnippet,
    goBackToBlocks,
} from "@website/js/tours/tour_utils";
import { patch } from "@web/core/utils/patch";

const patchWysiwygAdapter = () => {
    const { WysiwygAdapterComponent } = odoo.loader.modules.get("@website/components/wysiwyg_adapter/wysiwyg_adapter");
    return patch(WysiwygAdapterComponent.prototype, {
        _trigger_up(ev) {
            super._trigger_up(...arguments);
            if (ev.name === 'snippet_removed') {
                document.body.setAttribute("test-dd-snippet-removed", true);
            }
        }
    });
};

let unpatchWysiwygAdapter = null;

import { registry } from "@web/core/registry";

let snippetsNames = (new URL(document.location.href)).searchParams.get('snippets_names') || '';
// When this test is loaded in the backend, the search params aren't as easy to
// read as before. Little trickery to make this test run.
const searchParams = new URLSearchParams(window.location.search).get('path');
if (searchParams) {
    snippetsNames = new URLSearchParams(searchParams.split('/')[1]).get('snippets_names') || '';
    snippetsNames = snippetsNames.split(',');
}
const dropInOnlySnippets = {
    's_button': '.btn',
    's_video': '.media_iframe_video',
};
let steps = [];
let n = 0;
for (let snippet of snippetsNames) {
    n++;
    snippet = {
        name: snippet.split(':')[0],
        group: snippet.split(':')[1],
    };
    const isModal = ['s_popup', 's_newsletter_subscribe_popup'].includes(snippet.name);
    const isDropInOnlySnippet = Object.keys(dropInOnlySnippets).includes(snippet.name);

    let draggableElSelector = "";
    if (snippet.group) {
        draggableElSelector = `#oe_snippets .oe_snippet[data-snippet-group="${snippet.group}"] .oe_snippet_thumbnail`;
    } else {
        draggableElSelector = `#oe_snippets .oe_snippet:has( > [data-snippet="${snippet.name}"]) .oe_snippet_thumbnail`;
    }

    const snippetSteps = [{
        content: `Drop ${snippet.group || snippet.name} ${snippet.group ? "group" : "snippet"} [${n}/${snippetsNames.length}]`,
        trigger: draggableElSelector,
        run: "drag_and_drop :iframe #wrap .oe_drop_zone",
    }, {
        content: `Edit ${snippet.name} snippet`,
        trigger: `:iframe #wrap.o_editable [data-snippet='${snippet.name}']${isModal ? ' .modal.show' : ''}`,
        run: "click",
    }, {
        content: `check ${snippet.name} setting are loaded, wait panel is visible`,
        trigger: ".o_we_customize_panel",
    }, {
        content: `Remove the ${snippet.name} snippet`, // Avoid bad perf if many snippets
        trigger: "we-button.oe_snippet_remove:last",
        run: "click",
    },
    {
        trigger: "body[test-dd-snippet-removed]",
    },
    {
        content: `click on 'BLOCKS' tab (${snippet.name})`,
        trigger: ".o_we_add_snippet_btn",
        async run (actions) {
            document.body.removeAttribute("test-dd-snippet-removed");
            await actions.click();
        },
    }];

    if (snippet.group) {
        snippetSteps.splice(1, 0, {
            content: "Click on the snippet preview in the dialog",
            trigger: `:iframe .o_snippet_preview_wrap[data-snippet-id="${snippet.name}"]`,
            run: "click",
        });
    }

    if (snippet === 's_google_map') {
        snippetSteps.splice(2, 4, {
            content: 'Close API Key popup',
            trigger: ":iframe .modal-footer .btn-secondary",
            run: "click",
        });
    } else if (isModal) {
        snippetSteps.splice(4, 3, {
            content: `Hide the ${snippet.name} popup`,
            trigger: `:iframe [data-snippet='${snippet.name}'] .s_popup_close`,
            run: "click",
        }, {
            content: `Make sure ${snippet.name} is hidden`,
            trigger: ":iframe body:not(.modal-open)",
        });
    } else if (isDropInOnlySnippet) {
        // The 'drop in only' snippets have their 'data-snippet' attribute
        // removed once they are dropped, so we need to use a different selector.
        snippetSteps[1].trigger = `:iframe #wrap.o_editable ${dropInOnlySnippets[snippet.name]}`;
    }
    steps = steps.concat(snippetSteps);
}

registry.category("web_tour.tours").add("snippets_all_drag_and_drop", {
    checkDelay: 100,
    // To run the tour locally, you need to insert the URL sent by the python
    // tour here. There is currently an issue with tours which don't have an URL
    // url: '/?enable_editor=1&snippets_names=s_process_steps:columns,s_website_form:,s_...',
    steps: () => [
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Ensure snippets are actually passed at the test.",
        trigger: "body",
        run: function () {
            // safety check, otherwise the test might "break" one day and
            // receive no steps. The test would then not test anything anymore
            // without us noticing it.
            if (steps.length < 500) {
                console.error(`This test is not behaving as it should, got only ${steps.length} steps.`);
            }
            unpatchWysiwygAdapter = patchWysiwygAdapter();
        },
    },
    // This first step is needed as it will be used later for inner snippets
    // Without this, it will dropped inside the footer and will need an extra
    // selector.
    ...insertSnippet({
        id: "s_text_image",
        name: "Text - Image",
        groupName: "Content"
    }),
    {
        content: "Edit s_text_image snippet",
        trigger: ":iframe #wrap.o_editable [data-snippet='s_text_image']",
        run: "click",
    },
    {
        content: "check setting are loaded, wait panel is visible",
        trigger: ".o_we_customize_panel",
        run: "click",
    },
    goBackToBlocks(),
].concat(steps).concat([
    {
        content: "Remove wysiwyg patch",
        trigger: "body",
        run: () => unpatchWysiwygAdapter(),
    }
            ])
            .map((step) => {
                delete step.noPrepend;
                return step;
            }),
});
