odoo.define('im_livechat.legacy.im_livechat.Constants', function (require) {
"use strict";

// Constants
var LIVECHAT_COOKIE_HISTORY = 'im_livechat_history';
var HISTORY_LIMIT = 15;

var RATING_TO_EMOJI = {
    "5": "😊",
    "3": "😐",
    "1": "😞"
};

return {
    LIVECHAT_COOKIE_HISTORY: LIVECHAT_COOKIE_HISTORY,
    HISTORY_LIMIT: HISTORY_LIMIT,
    RATING_TO_EMOJI: RATING_TO_EMOJI,
};

});
