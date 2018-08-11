odoo.define('im_livechat.model.WebsiteLivechat', function (require) {
"use strict";

var AbstractThread = require('mail.model.AbstractThread');

var session = require('web.session');

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
var WebsiteLivechat = AbstractThread.extend({

    /**
     * @override
     * @private
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} params.data.anonymous_name
     * @param {boolean} [params.data.folded] states whether the livechat is
     *   folded or not. It is considered only if this is defined and it is a
     *   boolean.
     * @param {integer} params.data.id the ID of this livechat.
     * @param {integer} [params.data.message_unread_counter] the unread counter
     *   of this livechat.
     * @param {Array} params.data.operator_pid
     * @param {string} params.data.name the name of this livechat.
     * @param {string} [params.data.state] if 'folded', the livechat is folded.
     *   This is ignored if `folded` is provided and is a boolean value.
     * @param {string} params.data.uuid the UUID of this livechat.
     * @param {im_livechat.im_livechat.LivechatButton} params.parent
     */
    init: function (params) {
        this._super.apply(this, arguments);

        this._members = [];
        this._operatorPID = params.data.operator_pid;
        this._uuid = params.data.uuid;

        if (params.data.message_unread_counter !== undefined) {
            this._unreadCounter = params.data.message_unread_counter;
        }

        if (_.isBoolean(params.data.folded)) {
            this._folded = params.data.folded;
        } else {
            this._folded = params.data.state === 'folded';
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {im_livechat.model.WebsiteLivechatMessage[]}
     */
    getMessages: function () {
        return this._messages;
    },
    /**
     * @returns {Array}
     */
    getOperatorPID: function () {
        return this._operatorPID;
    },
    /**
     * @returns {string}
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * Increments the unread counter of this livechat by 1 unit.
     *
     * Note: this public method makes sense because the management of messages
     * for website livechat is external. This method should be dropped when
     * this class handles messages by itself.
     */
    incrementUnreadCounter: function () {
        this._incrementUnreadCounter();
    },
    /**
     * AKU: hack for the moment
     *
     * @param {im_livechat.model.WebsiteLivechatMessage[]} messages
     */
    setMessages: function (messages) {
        this._messages = messages;
    },
    /**
     * @returns {Object}
     */
    toData: function () {
        return {
            folded: this.isFolded(),
            id: this.getID(),
            message_unread_counter: this.getUnreadCounter(),
            operator_pid: this.getOperatorPID(),
            name: this.getName(),
            uuid: this.getUUID(),
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Warn that the unread counter has been updated on this livechat
     *
     * @override
     * @private
     */
    _warnUpdatedUnreadCounter: function () {
        this.trigger_up('updated_unread_counter');
    },
});

return WebsiteLivechat;

});
