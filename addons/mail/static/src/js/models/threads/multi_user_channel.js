odoo.define('mail.model.MultiUserChannel', function (require) {
"use strict";

var Channel = require('mail.model.Channel');

var MultiUserChannel = Channel.extend({
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {boolean} [params.data.mass_mailing=false]
     * @param {string} [params.data.public='public'] either 'public' or
     *   'private'
     */
    init: function (params) {
        this._super.apply(this, arguments);

        var data = params.data;

        this._isMassMailing = data.mass_mailing || false;
        this._type = 'multi_user_channel';
        this._public = data.public !== 'private';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the title to display in thread window's headers.
     * For channels, the title is prefixed with "#".
     *
     * @override
     * @returns {string|Object} the name of the thread by default (see getName)
     */
    getTitle: function () {
        return "#" + this._super.apply(this, arguments);
    },
    /**
     * States whether this thread has the mass mailing setting active or not.
     * This is a server-side setting, that determine the type of composer that
     * is used (basic or extended composer).
     *
     * @return {boolean}
     */
    isMassMailing: function () {
        return this._isMassMailing;
    },
    /**
     * @returns {boolean}
     */
    isPublic: function () {
        return this._public;
    },
    /**
     * Unsubscribes from channel
     *
     * @override
     * @returns {Promise} resolve when unsubscribed
     */
    unsubscribe: function () {
        return this._rpc({
            model: 'mail.channel',
            method: 'action_unfollow',
            args: [[this.getID()]],
        });
    },

});

return MultiUserChannel;

});
