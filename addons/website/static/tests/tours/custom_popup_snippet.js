/** @odoo-module */

import {
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const snippets = [
    { id: "s_popup", name: "Popup", groupName: "Content" },
    { id: "s_banner", name: "Banner", groupName: "Into" },
    { id: "s_popup", name: "Custom Popup", groupName: "Custom" },
];

registerWebsitePreviewTour(
    "custom_popup_snippet",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet(snippets[0]),
        ...clickOnSnippet(snippets[1]),
        {
            content: "save this snippet to save later",
            trigger: ".o_we_user_value_widget.fa-save",
            run: "click",
        },
        {
            content: "confirm and reload custom snippet",
            trigger: ".modal-footer > .btn.btn-primary",
            run: "click",
        },
        ...insertSnippet(snippets[2]),
        {
            content: "check whether new custom popup is visible or not.",
            trigger: ":iframe section[data-snippet='s_banner']",
        },
    ]
);
