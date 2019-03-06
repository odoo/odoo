odoo.define('im_livechat.model.WebsiteLivechat', function (require) {
"use strict";

var AbstractThread = require('mail.model.AbstractThread');
var ThreadTypingMixin = require('mail.model.ThreadTypingMixin');

var session = require('web.session');

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
var WebsiteLivechat = AbstractThread.extend(ThreadTypingMixin, {

    /**
     * @override
     * @private
     * @param {Object} params
     * @param {Object} params.data
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
        ThreadTypingMixin.init.call(this, arguments);

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

        // Necessary for thread typing mixin to display is typing notification
        // bar text (at least, for the operator in the members).
        this._members.push({
            id: this._operatorPID[0],
            name: this._operatorPID[1]
        });
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
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.isWebsiteUser
     * @returns {boolean}
     */
    _isTypingMyselfInfo: function (params) {
        return params.isWebsiteUser;
    },
    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.typing
     * @returns {Promise}
     */
    _notifyMyselfTyping: function (params) {
        return session.rpc('/im_livechat/notify_typing', {
            uuid: this.getUUID(),
            is_typing: params.typing,
        }, { shadow: true });
    },
    /**
     * Warn views that the list of users that are currently typing on this
     * livechat has been updated.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     */
    _warnUpdatedTypingPartners: function () {
        this.trigger_up('updated_typing_partners');
    },
    /**
     * Warn that the unread counter has been updated on this livechat
     *
     * @override
     * @private
     */
    _warnUpdatedUnreadCounter: function () {
        this.trigger_up('updated_unread_counter');
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Override so that it only unregister typing operators.
     *
     * Note that in the frontend, there is no way to identify a message that is
     * from the current user, because there is no partner ID in the session and
     * a message with an author sets the partner ID of the author.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _onTypingMessageAdded: function (message) {
        var operatorID = this.getOperatorPID()[0];
        if (message.hasAuthor() && message.getAuthorID() === operatorID) {
            this.unregisterTyping({ partnerID: operatorID });
        }
    },
});

return WebsiteLivechat;

});
