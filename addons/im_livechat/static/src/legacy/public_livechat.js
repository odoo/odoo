odoo.define('im_livechat.legacy.im_livechat.im_livechat', function (require) {
"use strict";

require('bus.BusService');
var utils = require('web.utils');

var { LIVECHAT_COOKIE_HISTORY, HISTORY_LIMIT, } = require('im_livechat.legacy.im_livechat.Constants');
var Feedback = require('im_livechat.legacy.im_livechat.Feedback');
var LivechatButton = require('im_livechat.legacy.im_livechat.LivechatButton');


// History tracking
var page = window.location.href.replace(/^.*\/\/[^/]+/, '');
var pageHistory = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
var urlHistory = [];
if (pageHistory) {
    urlHistory = JSON.parse(pageHistory) || [];
}
if (!_.contains(urlHistory, page)) {
    urlHistory.push(page);
    while (urlHistory.length > HISTORY_LIMIT) {
        urlHistory.shift();
    }
    utils.set_cookie(LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24); // 1 day cookie
}

return {
    LivechatButton: LivechatButton,
    Feedback: Feedback,
};

});

