odoo.define('im_livechat.legacy.im_livechat.HistoryTracking', function (require) {
"use strict";

const utils = require('web.utils');

const { HISTORY_LIMIT, LIVECHAT_COOKIE_HISTORY } = require ("im_livechat.legacy.im_livechat.Constants");

// History tracking
const page = window.location.href.replace(/^.*\/\/[^/]+/, '');
const pageHistory = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
let urlHistory = [];
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

});
