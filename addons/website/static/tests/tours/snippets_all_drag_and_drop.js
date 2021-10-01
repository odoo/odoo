odoo.define("website.tour.snippets_all_drag_and_drop", async function (require) {
"use strict";

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
        trigger: ".o_we_add_snippet_btn",
        run: function (actions) {
            // FIXME cannot find the reason why this setTimeout is needed to
            // after reverting ab7508393376075f95d6dd5925e7f4462936d2, to check
            // (this commit is however reverted temporarily until a better
            // solution is found).
            setTimeout(() => actions.auto(), 0);
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
        trigger: "#oe_snippets",
        run: function () {
            // safety check, otherwise the test might "break" one day and
            // receive no steps. The test would then not test anything anymore
            // without us noticing it.
            if (steps.lenth < 280) {
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
