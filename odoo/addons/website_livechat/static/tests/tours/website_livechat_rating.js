/** @odoo-module **/

import {
    start,
    endDiscussion,
    goodRating,
    okRating,
    sadRating,
    feedback,
    transcript,
    close,
} from "./website_livechat_common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_complete_flow_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(start, endDiscussion, okRating, feedback, transcript, close),
});

registry.category("web_tour.tours").add("website_livechat_happy_rating_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(start, endDiscussion, goodRating, feedback),
});

registry.category("web_tour.tours").add("website_livechat_ok_rating_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(start, endDiscussion, okRating, feedback),
});

registry.category("web_tour.tours").add("website_livechat_sad_rating_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(start, endDiscussion, sadRating, feedback),
});

registry.category("web_tour.tours").add("website_livechat_no_rating_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(start, endDiscussion, transcript, close),
});

registry.category("web_tour.tours").add("website_livechat_no_rating_no_close_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(start),
});
