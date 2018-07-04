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
     * @param {Object} params.data.id the ID of this thread
     */
    init: function (params) {
        this._id = params.data.id;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
     * @returns {boolean}
     */
    hasMessages: function () {
        return !_.isEmpty(this.getMessages());
    },
});

return AbstractThread;

});
