odoo.define("website.tour.snippets_all_drag_and_drop", async function (require) {
"use strict";

const snippetsEditor = require('web_editor.snippet.editor');

snippetsEditor.SnippetEditor.include({
    removeSnippet: async function (shouldRecordUndo = true) {
        await this._super(...arguments);
        $('body').attr('test-dd-snippet-removed', true);
    },
});

const tour = require("web_tour.tour");

let snippetsNames = (new URL(document.location.href)).searchParams.get('snippets_names') || '';
snippetsNames = snippetsNames.split(',');
let steps = [];
let n = 0;
for (const snippet of snippetsNames) {
    n++;
    const snippetSteps = [{
        content: `Drop ${snippet} snippet [${n}/${snippetsNames.length}]`,
        trigger: `#oe_snippets .oe_snippet:has( > [data-snippet='${snippet}']) .oe_snippet_thumbnail`,
        run: "drag_and_drop #wrap",
    }, {
        content: `Edit ${snippet} snippet`,
        trigger: `#wrap.o_editable [data-snippet='${snippet}']`,
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
            trigger: ".modal-footer .btn-secondary",
        });
    } else if (['s_popup', 's_newsletter_subscribe_popup'].includes(snippet)) {
        snippetSteps[2]['in_modal'] = false;
        snippetSteps.splice(3, 2, {
            content: `Hide the ${snippet} popup`,
            trigger: ".s_popup_close",
        });
    }
    steps = steps.concat(snippetSteps);
}

tour.register("snippets_all_drag_and_drop", {
    test: true,
}, [
    {
        content: "Ensure snippets are actually passed at the test.",
        trigger: "body",
        run: function () {
            // safety check, otherwise the test might "break" one day and
            // receive no steps. The test would then not test anything anymore
            // without us noticing it.
            if (steps.length < 220) {
                console.error("This test is not behaving as it should.");
            }
        },
    },
    // This first step is needed as it will be used later for inner snippets
    // Without this, it will dropped inside the footer and will need an extra
    // selector.
    {
        content: "Drop s_text_image snippet",
        trigger: "#oe_snippets .oe_snippet:has( > [data-snippet='s_text_image']) .oe_snippet_thumbnail",
        run: "drag_and_drop #wrap"
    },
    {
        content: "Edit s_text_image snippet",
        trigger: "#wrap.o_editable [data-snippet='s_text_image']"
    },
    {
        content: "check setting are loaded, wait panel is visible",
        trigger: ".o_we_customize_panel"
    },
    {
        content: "click on 'BLOCKS' tab",
        trigger: ".o_we_add_snippet_btn"
    },
].concat(steps)
);
});
