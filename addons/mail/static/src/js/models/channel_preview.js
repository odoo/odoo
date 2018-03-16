odoo.define('mail.model.ChannelPreview', function (require) {
"use strict";

var ConversationPreview = require('mail.model.ConversationPreview');
var utils = require('mail.utils');

var ChannelPreview = ConversationPreview.extend({
    /**
     * @param {mail.model.Channel} channel
     */
    init: function (channel) {
        this._channel = channel;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @return {integer|string}
     */
    getID: function () {
        return this._channel.getID();
    },
    /**
     * @override
     * @return {string}
     */
    getImageSource: function () {
        if (!this.isChat()) {
            return '/web/image/mail.channel/' + this._channel.getID() + '/image_small';
        } else if (this._channel.directPartnerID) {
            return '/web/image/res.partner/' + this._channel.directPartnerID + '/image_small';
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    },
    /**
     * @override
     * @return {moment}
     */
    getLastMessageDate: function () {
        if (this._channel.hasMessages()) {
            return this._channel.getLastMessage().getDate();
        }
        return moment();
    },
    /**
     * @override
     * @return {string}
     */
    getLastMessageDisplayedAuthor: function () {
        if (!this._channel.hasMessages()) {
            return '';
        }
        return this._channel.getLastMessage().getDisplayedAuthor();
    },
    /**
     * @override
     * @return {string}
     */
    getLastMessagePreview: function () {
        return utils.parse_and_transform(this._channel.getLastMessage().getBody(), utils.inline);
    },
    /**
     * @override
     * @return {string}
     */
    getName: function () {
        return this._channel.getName();
    },
    /**
     * @override
     * @return {string}
     */
    getStatus: function () {
        return this._channel.getStatus();
    },
    /**
     * @override
     * @return {integer}
     */
    getUnreadCounter: function () {
        return this._channel.getUnreadCounter();
    },
    /**
     * @override
     * @return {boolean}
     */
    hasLastMessage: function () {
        return !!this._channel.getLastMessage();
    },
    /**
     * @override
     * @return {boolean}
     */
    hasUnreadMessages: function () {
        return this._channel.getUnreadCounter() > 0;
    },
    /**
     * @override
     * @return {boolean}
     */
    isChat: function () {
        return this._channel.isChat();
    },
    /**
     * @return {boolean}
     */
    isComplete: function () {
        return this._channel.hasBeenPreviewed();
    },
    /**
     * @override
     * @return {boolean}
     */
    isLastMessageAuthor: function () {
        if (!this._channel.hasMessages()) {
            return false;
        }
        return this._channel.getLastMessage().isAuthor();
    },

});

return ChannelPreview;

});
