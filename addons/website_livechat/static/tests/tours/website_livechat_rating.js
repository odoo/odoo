odoo.define('website_livechat.tour', function(require) {
'use strict';

var commonSteps = require("website_livechat.tour_common");
var tour = require("web_tour.tour");

tour.register('website_livechat_complete_flow_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.okRatingStep, commonSteps.feedbackStep, commonSteps.transcriptStep, commonSteps.closeStep));

tour.register('website_livechat_happy_rating_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.goodRatingStep));

tour.register('website_livechat_ok_rating_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.okRatingStep, commonSteps.feedbackStep));

tour.register('website_livechat_sad_rating_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.sadRatingStep, commonSteps.feedbackStep));

tour.register('website_livechat_no_rating_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.startStep, commonSteps.endDiscussionStep, commonSteps.transcriptStep, commonSteps.closeStep));

tour.register('website_livechat_no_rating_no_close_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.startStep));

return {};
});
