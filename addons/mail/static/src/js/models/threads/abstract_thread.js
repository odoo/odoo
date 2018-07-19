odoo.define('mail.model.AbstractThread', function (require) {
"use strict";

var Class = require('web.Class');

/**
 * Abstract thread is the super class of all threads, either backend threads
 * (which are compatible with mail service) or website livechats.
 *
 * Abstract threads contain abstract messages
 */
var AbstractThread = Class.extend({
    /**
     * @param {Object} params
     * @param {Object} params.data
     * @param {integer|string} params.data.id the ID of this thread
     * @param {string} params.data.name the name of this thread
     * @param {string} params.data.status the status of this thread
     */
    init: function (params) {
        this._folded = false; // threads are unfolded by default
        this._id = params.data.id;
        this._name = params.data.name;
        this._status = params.data.status;
        this._unreadCounter = 0; // amount of messages not yet been read
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the folded state of the thread
     *
     * @param {boolean} folded
     */
    fold: function (folded) {
        this._folded = folded;
    },
    /**
     * Get the ID of this thread
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._id;
    },
    /**
     * @abstract
     * @returns {mail.model.AbstractMessage[]}
     */
    getMessages: function () {},
    /**
     * Get the name of this thread. If the name of the thread has been created
     * by the user from an input, it may be escaped.
     *
     * @returns {string}
     */
    getName: function () {
        return this._name;
    },
    /**
     * Get the status of the thread (e.g. 'online', 'offline', etc.)
     *
     * @returns {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * Returns the title to display in thread window's headers.
     *
     * @returns {string} the name of the thread by default (see @getName)
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
     * @returns {boolean}
     */
    hasMessages: function () {
        return !_.isEmpty(this.getMessages());
    },
    /**
     * Increments the unread counter of this thread by 1 unit.
     */
    incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * States whether this thread is folded or not.
     *
     * @return {boolean}
     */
    isFolded: function () {
        return this._folded;
    },
    /**
     * Resets the unread counter of this thread to 0.
     */
    resetUnreadCounter: function () {
        this._unreadCounter = 0;
    },
});

return AbstractThread;

});
