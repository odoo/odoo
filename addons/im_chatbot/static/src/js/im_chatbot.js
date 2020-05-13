odoo.define('im_chatbot.chatBot', function (require) {
    "use strict";

    var LivechatButton = require('im_livechat.im_livechat').LivechatButton;

    LivechatButton.include({
        init: function (parent, serverURL, options) {
            this._super(...arguments);
        }
    });

    return {
        LivechatButton: LivechatButton,
    };
});
