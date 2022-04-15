odoo.define('im_livechat.legacy.im_livechat.Constants', function (require) {
"use strict";

// Constants
const LIVECHAT_COOKIE_HISTORY = 'im_livechat_history';
const HISTORY_LIMIT = 15;

const RATING_TO_EMOJI = {
    "5": "😊",
    "3": "😐",
    "1": "😞"
};

return {
    LIVECHAT_COOKIE_HISTORY,
    HISTORY_LIMIT,
    RATING_TO_EMOJI,
};

});
