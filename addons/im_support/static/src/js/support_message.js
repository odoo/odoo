odoo.define('im_support.SupportMessage', function (require) {
"use strict";

var Message = require('mail.model.Message');

var session = require('web.session');

/**
 * This is a model for messages that are in the the support channel
 */
var SupportMessage = Message.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this._serverAuthorID !== this.call('mail_service', 'getOdoobotID')) {
            if (!this._serverAuthorID[0]) {
                // the author is the client
                this._serverAuthorID = [session.partner_id, session.name];
            } else {
                // the author is the operator
                // prevent from conflicting with partners of this instance
                this._serverAuthorID[0] = -1;
            }
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {string}
     */
    getAvatarSource: function () {
        return '/mail/static/src/img/odoo_o.png';
    },
    /**
     * Overrides to prevent clicks on the Support operator from redirecting.
     *
     * @override
     * @returns {boolean}
     */
    shouldRedirectToAuthor: function () {
        return false;
    },
    /**
     * Overrides to prevent from calling the server for messages of the Support
     * channel (which are records on the Support database).
     *
     * @override
     * @returns {$.Promise}
     */
    toggleStarStatus: function () {
        return $.when();
    },
});

return SupportMessage;

});
