odoo.define('mail.model.ConversationPreview', function (require) {
"use strict";

var Class = require('web.Class');

var ConversationPreview = Class.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @abstract
     * @return {integer|string}
     */
    getID: function () {},
    /**
     * @abstract
     * @return {string}
     */
    getImageSource: function () {},
    /**
     * @abstract
     * @return {moment}
     */
    getLastMessageDate: function () {},
    /**
     * @abstract
     * @return {string}
     */
    getLastMessageDisplayedAuthor: function () {},
    /**
     * @return {string}
     */
    getLastMessagePreview: function () {},
    /**
     * @return {string|undefined}
     */
    getModel: function () {
        return undefined;
    },
    /**
     * @abstract
     * @return {string}
     */
    getName: function () {},
    /**
     * @return {integer|undefined}
     */
    getResID: function () {
        return undefined;
    },
    /**
     * @abstract
     * @return {string}
     */
    getStatus: function () {},
    /**
     * @abstract
     * @return {integer}
     */
    getUnreadCounter: function () {},
    /**
     * @abstract
     * @return {boolean}
     */
    hasLastMessage: function () {},
    /**
     * @abstract
     * @return {boolean}
     */
    hasUnreadMessages: function () {},
    /**
     * @abstract
     * @return {boolean}
     */
    isChat: function () {},
    /**
     * @abstract
     * @return {boolean}
     */
    isLastMessageAuthor: function () {},

});

return ConversationPreview;

});
