odoo.define('im_livechat.model.WebsiteLivechat', function (require) {
"use strict";

var AbstractThread = require('mail.model.AbstractThread');

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
var WebsiteLivechat = AbstractThread.extend({
    /**
     * @param {Object} livechatData
     * @param {boolean} [livechatData.folded] states whether the livechat is
     *   folded or not. It is considered only if this is defined and it is a
     *   boolean value.
     * @param {integer} livechatData.id the ID of this livechat.
     * @param {integer} [livechatData.message_unread_counter=0] the unread
     *   counter of this livechat.
     * @param {Array} livechatData.operator_pid
     * @param {string} livechatData.name the name of this livechat.
     * @param {string} [livechatData.state] if 'folded', the livechat is folded.
     *   This is ignored if `folded` is provided and is a boolean value.
     * @param {string} livechatData.uuid the UUID of this livechat.
     */
    init: function (livechatData) {
        var params = { data: livechatData };

        this._super(params);

        this._folded = false;
        this._name = livechatData.name;
        this._operatorPID = livechatData.operator_pid;
        this._unreadCounter = livechatData.message_unread_counter || 0;
        this._uuid = livechatData.uuid;

        if (_.isBoolean(livechatData.folded)) {
            this._folded = livechatData.folded;
        } else {
            this._folded = livechatData.state === 'folded';
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {im_livechat.model.WebsiteLivechatMessage[]}
     */
    getMessages: function () {
        return this._messages;
    },
    /**
     * @returns {string}
     */
    getName: function () {
        return this._name;
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
    getTitle: function () {
        return this.getName();
    },
    /**
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * @returns {string}
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * Increments the unread counter of this livechat by 1 unit.
     */
    incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * @returns {boolean}
     */
    isFolded: function () {
        return this._folded;
    },
    /**
     * Resets the unread counter of this livechat to 0.
     */
    resetUnreadCounter: function () {
        this._unreadCounter = 0;
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
    /**
     * @param {boolean} folded
     */
    updateFoldState: function (folded) {
        this._folded = folded;
    },
});

return WebsiteLivechat;

});
