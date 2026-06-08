import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("client_action_iframe_fallback", {}, () => [
    {
        content: "Ensure we are on the expected page",
        trigger: ':iframe html[data-view-xmlid="website.homepage"]',
    },
    {
        content: "Ensure the iframe fallback is not loaded in test mode",
        trigger: `body:not(:has(iframe[src="/website/iframefallback"]))`,
    },
]);
