import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const message = ".o_action_manager .alert:contains(This page is not published)";

registerWebsitePreviewTour("website_publish_page_message", {}, () => [
    {
        content: "Check that the message is displayed on the unpublished page",
        trigger: `${message} button.btn-primary:contains(Publish)`,
    },
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check that the message is hidden in edit mode",
        trigger: `body:not(:has(${message}))`,
    },
    ...clickOnSave(),
    {
        content: "Publish the page from the message",
        trigger: `${message} button.btn-primary:contains(Publish)`,
        run: "click",
    },
    {
        content: "Check that the message is removed and that the page is published",
        trigger: `body:not(:has(${message})) .o_website_publish_container input:checked`,
    },
    {
        content: "Unpublish the page from the navbar",
        trigger: ".o_website_publish_container a",
        run: "click",
    },
    {
        content: "Check that the page is unpublished",
        trigger: ".o_website_publish_container input:not(:checked)",
    },
    {
        content: "Check that the message is displayed again",
        trigger: message,
    },
]);
