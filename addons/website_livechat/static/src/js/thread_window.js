odoo.define('website_livechat.ThreadWindow', function (require) {
"use strict";

var ThreadWindow = require('mail.ThreadWindow');
var session = require('web.session');

/**
 * This is the main widget for rendering small windows for mail.model.Thread.
 * Almost all instances of this class are linked to a thread. The sole
 * exception is the "blank" thread window. This window let us open another
 * thread window, using this "blank" thread window.
 */
ThreadWindow.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        var self = this;
        if (this.hasThread() && this._thread._type === "livechat" && this._threadWidget._messages.length == 0) {
            session.rpc('/im_livechat/close_empty_livechat', {uuid: this._thread._uuid});
        }
        else {
            this._super();
        }
    },
});

return ThreadWindow;

});
