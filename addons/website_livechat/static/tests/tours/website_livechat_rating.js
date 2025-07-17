import {
    start,
    closeChat,
    goodRating,
    okRating,
    sadRating,
    feedback,
    downloadTranscript,
    emailTranscript,
    close,
    confirmnClose,
} from "./website_livechat_common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_complete_flow_tour", {
    url: "/",
    steps: () =>
        [].concat(start, closeChat, confirmnClose, okRating, feedback, downloadTranscript, close),
});

registry.category("web_tour.tours").add("website_livechat_complete_flow_tour_logged_in", {
    url: "/",
    steps: () =>
        [].concat(start, closeChat, confirmnClose, okRating, feedback, emailTranscript, close),
});

registry.category("web_tour.tours").add("website_livechat_happy_rating_tour", {
    url: "/",
    steps: () => [].concat(start, closeChat, confirmnClose, goodRating, feedback),
});

registry.category("web_tour.tours").add("website_livechat_ok_rating_tour", {
    url: "/",
    steps: () => [].concat(start, closeChat, confirmnClose, okRating, feedback),
});

registry.category("web_tour.tours").add("website_livechat_sad_rating_tour", {
    url: "/",
    steps: () => [].concat(start, closeChat, confirmnClose, sadRating, feedback),
});

registry.category("web_tour.tours").add("website_livechat_no_rating_tour", {
    url: "/",
    steps: () => [].concat(start, closeChat, confirmnClose, downloadTranscript, close),
});

registry.category("web_tour.tours").add("website_livechat_no_rating_no_close_tour", {
    url: "/",
    steps: () => [].concat(start),
});
