/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour("dynamic_snippet_undo_removal",
    {
        test: true,
        edition: true,
        url: "/?debug=1",
    },
    () => [
        wTourUtils.dragNDrop({
            id: "s_dynamic_snippet",
            name: "Dynamic Snippet",
        }),
        wTourUtils.clickOnSnippet({
            id: "s_dynamic_snippet",
            name: "Dynamic Snippet",
        }),
        {
            content: "Remove the dynamic snippet",
            trigger: "iframe .oe_overlay.oe_active .oe_snippet_remove",
        },
        {
            content: "Check that the dynamic snippet is removed",
            trigger: "iframe:not('.s_dynamic_snippet')",
            isCheck: true,
        },
        {
            content: "Undo the deletion",
            trigger: "button[data-action='undo']",
        },
        {
            content: "Check that the dynamic snippet is back",
            trigger: "iframe .s_dynamic_snippet",
            isCheck: true,
        },
        {
            content: "Undo Again to remove the dynamic snippet",
            trigger: "button[data-action='undo']",
        },
        {
            content: "Check that the dynamic snippet is not present anymore",
            trigger: "iframe:not('.s_dynamic_snippet')",
            isCheck: true,
        }
    ]
);
