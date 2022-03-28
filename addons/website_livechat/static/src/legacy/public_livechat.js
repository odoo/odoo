odoo.define('website_livechat.legacy.website_livechat.livechat_request', function (require) {
"use strict";

var utils = require('web.utils');
var LivechatButton = require('im_livechat.legacy.im_livechat.im_livechat').LivechatButton;


LivechatButton.include({
    className: `${LivechatButton.prototype.className} o_bottom_fixed_element`,

    /**
     * @override
     * Check if a chat request is opened for this visitor
     * if yes, replace the session cookie and start the conversation immediately.
     * Do this before calling super to have everything ready before executing existing start logic.
     * This is used for chat request mechanism, when an operator send a chat request
     * from backend to a website visitor.
     */
    willStart: function () {
        if (this.options.chat_request_session) {
            utils.set_cookie('im_livechat_session', JSON.stringify(this.options.chat_request_session), 60*60);
        }
        return this._super();
    },
    /**
     * @override
     */
     start() {
        // We trigger a resize to launch the event that checks if this element hides
        // a button when the page is loaded.
        $(window).trigger('resize');
        return this._super(...arguments);
    },
});

return {
    LivechatButton: LivechatButton,
};

});
