/** @odoo-module */

import wTourUtils from "website.tour_utils";

const snippets = [
    { id: "s_popup", name: "Popup" },
    { id: "s_popup", name: "Custom Popup" },
];
wTourUtils.registerWebsitePreviewTour(
    "custom_popup_snippet",
    {
        test: true,
        url: "/",
        edition: true,
    },
    [
        wTourUtils.dragNDrop(snippets[0]),
        wTourUtils.clickOnSnippet(snippets[0]),
        {
            content: "save this snippet to save later",
            trigger: ".o_we_user_value_widget.fa-save",
        },
        {
            content: "confirm and reload custom snippet",
            trigger: ".modal-footer > .btn.btn-primary",
        },
        wTourUtils.dragNDrop(snippets[1]),
        {
            content: "check whether new custom popup is visible or not.",
            trigger: "iframe #wrap.o_editable [data-name='Custom Popup']",
            run: () => {}, // This is a check
        },
    ]
);
