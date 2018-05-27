odoo.define('mail.model.MessagePreview', function (require) {
"use strict";

var ConversationPreview = require('mail.model.ConversationPreview');
var utils = require('mail.utils');

var MessagePreview = ConversationPreview.extend({
    /**
     * @param {mail.model.Message} message
     * @param {integer} unreadCounter
     */
    init: function (message, unreadCounter) {
        this._message = message;
        this._unreadCounter = unreadCounter;
    },


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @return {string}
     */
    getID: function () {
        return 'mailbox_inbox';
    },
    /**
     * @override
     * @return {string}
     */
    getImageSource: function () {
        return this._message.getModuleIcon() ||
                this._message.getAvatarSource();
    },
    /**
     * @override
     * @return {moment}
     */
    getLastMessageDate: function () {
        return this._message.getDate();
    },
    /**
     * @override
     * @return {string}
     */
    getLastMessageDisplayedAuthor: function () {
        return this._message.getDisplayedAuthor();
    },
    /**
     * @override
     * @return {string}
     */
    getLastMessagePreview: function () {
        return utils.parse_and_transform(this._message.getBody(), utils.inline);
    },
    /**
     * @override
     * @return {string|undefined}
     */
    getModel: function () {
        return this._message.getDocumentModel();
    },
    /**
     * @override
     * @return {string}
     */
    getName: function () {
        return this._message.isLinkedToDocument() ? this._message.getDocumentName() :
                this._message.hasSubject() ? this._message.getSubject() :
                this._message.getDisplayedAuthor();
    },
    /**
     * @override
     * @return {integer|undefined}
     */
    getResID: function () {
        return this._message.getDocumentResID();
    },
    /**
     * @override
     * @return {string}
     */
    getStatus: function () {
        return this._message.status;
    },
    /**
     * @override
     * @return {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * @override
     * @return {boolean}
     */
    hasLastMessage: function () {
        return true;
    },
    /**
     * @override
     * @return {boolean}
     */
    hasUnreadMessages: function () {
        return this._unreadCounter > 0;
    },
    /**
     * @override
     * @return {boolean}
     */
    isChat: function () {
        return false;
    },
    /**
     * @override
     * @return {boolean}
     */
    isLastMessageAuthor: function () {
        return false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Object} fake last message of preview, short version of itself
     */
    _getLastMessage: function () {
        return {
            body: this._message.getBody(),
            date: this._message.getDate(),
            displayedAuthor: this._message.getDisplayedAuthor(),
        };
    },

});

return MessagePreview;

});
