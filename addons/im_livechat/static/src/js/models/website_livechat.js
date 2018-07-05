odoo.define('im_livechat.model.WebsiteLivechat', function (require) {
"use strict";

var AbstractThread = require('mail.AbstractThread');

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
var WebsiteLivechat = AbstractThread.extend({
    /**
     * @param {Object} livechatData
     * @param {integer} livechatData.id the ID of this livechat.
     * @param {integer} [livechatData.message_unread_counter=0] the unread
     *   counter of this livechat.
     * @param {string} livechatData.name the name of this livechat.
     * @param {string} livechatData.state if 'folded', the livechat is folded.
     */
    init: function (livechatData) {
        var params = { data: livechatData };

        this._super(params);

        this._folded = livechatData.state === 'folded';
        this._name = livechatData.name;
        this._unreadCounter = livechatData.message_unread_counter || 0;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @abstract
     * @returns {mail.model.AbstractMessage[]}
     */
    getMessages: function () {},
    /**
     * @returns {string}
     */
    getTitle: function () {
        return this._name;
    },
    /**
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * Increments the unread counter of this livechat by 1 unit.
     */
    incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * Resets the unread counter of this livechat to 0.
     */
    resetUnreadCounter: function () {
        this._unreadCounter = 0;
    },
    /**
     * @param {boolean} folded
     */
    updateFoldState: function (folded) {
        this._folded = folded;
    },
});

return WebsiteLivechat;

});
