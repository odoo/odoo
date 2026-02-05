import {
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("visitor_tracking", {}, () => [
    {
        content: "link to tracked page",
        trigger: "#tracked_link",
        run: "click",
        expectUnloadPage: true,
    },
]);
