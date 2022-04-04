odoo.define('im_livechat.legacy.im_livechat.HistoryTracking', function (require) {
"use strict";

var utils = require('web.utils');

var { HISTORY_LIMIT, LIVECHAT_COOKIE_HISTORY } = require ("im_livechat.legacy.im_livechat.Constants");

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
    utils.set_cookie(LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24, 'optional'); // 1 day cookie
}

});
