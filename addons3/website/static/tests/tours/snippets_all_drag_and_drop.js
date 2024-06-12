/** @odoo-module **/

import websiteTourUtils from "@website/js/tours/tour_utils";
import { patch } from "@web/core/utils/patch";

const patchWysiwygAdapter = () => {
    const { WysiwygAdapterComponent } = odoo.loader.modules.get("@website/components/wysiwyg_adapter/wysiwyg_adapter");
    return patch(WysiwygAdapterComponent.prototype, {
        _trigger_up(ev) {
            super._trigger_up(...arguments);
            if (ev.name === 'snippet_removed') {
                $('body').attr('test-dd-snippet-removed', true);
            }
        }
    });
};

let unpatchWysiwygAdapter = null;

import { registry } from "@web/core/registry";

let snippetsNames = (new URL(document.location.href)).searchParams.get('snippets_names') || '';
// When this test is loaded in the backend, the search params aren't as easy to
// read as before. Little trickery to make this test run.
const searchParams = new URLSearchParams(window.location.href.split('#')[1]).get('path');
if (searchParams) {
    snippetsNames = new URLSearchParams(searchParams.split('/')[1]).get('snippets_names') || '';
    snippetsNames = snippetsNames.split(',');
}
const dropInOnlySnippets = {
    's_button': '.btn',
    's_image': '.img',
    's_video': '.media_iframe_video',
};
let steps = [];
let n = 0;
for (const snippet of snippetsNames) {
    n++;
    const isModal = ['s_popup', 's_newsletter_subscribe_popup'].includes(snippet);
    const isDropInOnlySnippet = Object.keys(dropInOnlySnippets).includes(snippet);
    const snippetSteps = [{
        content: `Drop ${snippet} snippet [${n}/${snippetsNames.length}]`,
        trigger: `#oe_snippets .oe_snippet:has( > [data-snippet='${snippet}']) .oe_snippet_thumbnail`,
        run: "drag_and_drop_native iframe #wrap",
    }, {
        content: `Edit ${snippet} snippet`,
        trigger: `iframe #wrap.o_editable [data-snippet='${snippet}']${isModal ? ' .modal.show' : ''}`,
    }, {
        content: `check ${snippet} setting are loaded, wait panel is visible`,
        trigger: ".o_we_customize_panel",
        run: function () {}, // it's a check
    }, {
        content: `Remove the ${snippet} snippet`, // Avoid bad perf if many snippets
        trigger: "we-button.oe_snippet_remove:last"
    }, {
        content: `click on 'BLOCKS' tab (${snippet})`,
        extra_trigger: 'body[test-dd-snippet-removed]',
        trigger: ".o_we_add_snippet_btn",
        run: function (actions) {
            $('body').removeAttr('test-dd-snippet-removed');
            actions.auto();
        },
    }];

    if (snippet === 's_google_map') {
        snippetSteps.splice(1, 3, {
            content: 'Close API Key popup',
            trigger: "iframe .modal-footer .btn-secondary",
        });
    } else if (isModal) {
        snippetSteps[2]['in_modal'] = false;
        snippetSteps.splice(3, 2, {
            content: `Hide the ${snippet} popup`,
            trigger: `iframe [data-snippet='${snippet}'] .s_popup_close`,
        }, {
            content: `Make sure ${snippet} is hidden`,
            trigger: "iframe body:not(.modal-open)",
        });
    } else if (isDropInOnlySnippet) {
        // The 'drop in only' snippets have their 'data-snippet' attribute
        // removed once they are dropped, so we need to use a different selector.
        snippetSteps[1]['trigger'] = `iframe #wrap.o_editable ${dropInOnlySnippets[snippet]}`;
    }
    steps = steps.concat(snippetSteps);
}

registry.category("web_tour.tours").add("snippets_all_drag_and_drop", {
    test: true,
    // To run the tour locally, you need to insert the URL sent by the python
    // tour here. There is currently an issue with tours which don't have an URL
    // url: '/?enable_editor=1&snippets_names=s_showcase,s_numbers,s_...',
    steps: () => [
    ...websiteTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Ensure snippets are actually passed at the test.",
        trigger: "body",
        run: function () {
            // safety check, otherwise the test might "break" one day and
            // receive no steps. The test would then not test anything anymore
            // without us noticing it.
            if (steps.length < 220) {
                console.error(`This test is not behaving as it should, got only ${steps.length} steps.`);
            }
            unpatchWysiwygAdapter = patchWysiwygAdapter();
        },
    },
    // This first step is needed as it will be used later for inner snippets
    // Without this, it will dropped inside the footer and will need an extra
    // selector.
    websiteTourUtils.dragNDrop({
        id: "s_text_image",
        name: "Text - Image"
    }),
    {
        content: "Edit s_text_image snippet",
        trigger: "iframe #wrap.o_editable [data-snippet='s_text_image']"
    },
    {
        content: "check setting are loaded, wait panel is visible",
        trigger: ".o_we_customize_panel"
    },
    websiteTourUtils.goBackToBlocks(),
].concat(steps).concat([
    {
        content: "Remove wysiwyg patch",
        trigger: "body",
        run: () => unpatchWysiwygAdapter(),
    }
]),
});
