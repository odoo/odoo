/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

function dropSnippet(id, name, selector) {
    return [
        wTourUtils.dragNDrop({ id, name }),
        {
            content: `Check ${name} snippet is dropped`,
            trigger: `iframe #wrapwrap ${selector}`,
            run() {},
        },
    ];
}

function clickUndoRedo(action, waitSelector) {
    const btnClass = action === "undo" ? ".fa-undo" : ".fa-repeat";
    return [
        wTourUtils.clickOnElement(`${action} Button`, btnClass),
        {
            content: `Click ${action} action`,
            trigger: waitSelector,
            run() {},
        },
    ];
}

function checkNoBadge(content) {
    return {
        content,
        trigger: "iframe header .navbar:not(:has(.s_badge))",
        run() {},
    };
}

wTourUtils.registerWebsitePreviewTour(
    "undo_redo_header_oriented_issue",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        // --- Drop multiple snippets ---
        ...dropSnippet("s_media_list", "Media List", ".s_media_list"),
        ...dropSnippet("s_three_columns", "Columns", ".s_three_columns"),
        ...dropSnippet("s_banner", "Banner", ".s_banner"),
        ...dropSnippet("s_text_image", "Text - Image", ".s_text_image"),

        // --- Scroll to header ---
        {
            content: "Scroll to the header",
            trigger: "iframe #wrapwrap",
            run() {
                this.$anchor[0].scrollTo({ top: 0, left: 0 });
            },
        },

        // --- Add Badge snippet into header ---
        {
            content: "Drag the badge building block and drop it at the bottom of the page header.",
            trigger: `#oe_snippets .oe_snippet[name="Badge"] .oe_snippet_thumbnail:not(.o_we_already_dragging)`,
            run: "drag_and_drop_native iframe #wrapwrap > header .navbar",
        },
        {
            content: "Check badge is dropped in the header",
            trigger: ".oe_snippet_thumbnail:not(.o_we_already_dragging)",
            run() {},
        },

        // --- Undo twice ---
        ...clickUndoRedo("undo", "iframe #wrapwrap > header :not(.s_badge)"),
        ...clickUndoRedo("undo", "iframe #wrapwrap :not(.s_text_image)"),
        checkNoBadge("Check that badge is removed after 2 undos."),

        // --- Undo two more (total 4) ---
        ...clickUndoRedo("undo", "iframe #wrapwrap :not(.s_banner)"),
        ...clickUndoRedo("undo", "iframe #wrapwrap :not(.s_three_columns)"),
        checkNoBadge("Check that badge is still removed after 4 undos."),

        // --- Redo steps ---
        ...clickUndoRedo("redo", "iframe #wrapwrap .s_three_columns"),
        ...clickUndoRedo("redo", "iframe #wrapwrap .s_banner"),
        ...clickUndoRedo("redo", "iframe #wrapwrap .s_text_image"),
        {
            content: "Check that Contact Us button is not duplicated after 3 redos.",
            trigger: `iframe header .navbar-nav :has(> .btn.btn-primary.btn_cta) :not(:has(> .btn.btn-primary.btn_cta:nth-of-type(2)))`,
            run() {},
        },
    ]
);
