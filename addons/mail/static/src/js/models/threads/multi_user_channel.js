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
        this._type = data.public !== 'private' ? 'public' : 'private';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
     * Unsubscribes from channel
     *
     * @override
     * @returns {$.Promise} resolve when unsubscribed
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
