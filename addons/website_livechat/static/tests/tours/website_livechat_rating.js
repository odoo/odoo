/** @odoo-module alias=website_livechat.tour **/

import commonSteps from "website_livechat.tour_common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_livechat_complete_flow_tour', {
    test: true,
    url: '/',
    shadowDOM: ".o_livechat_root",
    steps: [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.okRatingStep, commonSteps.feedbackStep, commonSteps.transcriptStep, commonSteps.closeStep)});

registry.category("web_tour.tours").add('website_livechat_happy_rating_tour', {
    test: true,
    url: '/',
    shadowDOM: ".o_livechat_root",
    steps: [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.goodRatingStep, commonSteps.feedbackStep)});

registry.category("web_tour.tours").add('website_livechat_ok_rating_tour', {
    test: true,
    url: '/',
    shadowDOM: ".o_livechat_root",
    steps: [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.okRatingStep, commonSteps.feedbackStep)});

registry.category("web_tour.tours").add('website_livechat_sad_rating_tour', {
    test: true,
    url: '/',
    shadowDOM: ".o_livechat_root",
    steps: [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.sadRatingStep, commonSteps.feedbackStep)});

registry.category("web_tour.tours").add('website_livechat_no_rating_tour', {
    test: true,
    url: '/',
    shadowDOM: ".o_livechat_root",
    steps: [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.transcriptStep, commonSteps.closeStep)});

registry.category("web_tour.tours").add('website_livechat_no_rating_no_close_tour', {
    test: true,
    url: '/',
    shadowDOM: ".o_livechat_root",
    steps: [].concat(commonSteps.startStep)});

export default {};
