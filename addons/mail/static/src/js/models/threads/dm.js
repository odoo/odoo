odoo.define('mail.model.DM', function (require) {
"use strict";

var Channel = require('mail.model.Channel');

/**
 *
 * Any piece of code in JS that make use of DMs must ideally interact with
 * such objects, instead of direct data from the server.
 */
var DM = Channel.extend({
    /**
     * @override
     * @param {Object} data
     * @param {Object} data.direct_partner
     * @param {integer} data.direct_partner[0].id
     * @param {string} data.direct_partner[0].im_status
     * @param {string} data.direct_partner[0].name
     */
    init: function (parent, data) {
        this._super.apply(this, arguments);

        this._type = 'dm';
        this._name = data.direct_partner[0].name;
        this._directPartnerID = data.direct_partner[0].id;
        this._status = data.direct_partner[0].im_status;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the direct partner ID linked to the DM, i.e. the partner ID of the
     * user at the other end of the DM conversation. All DM do have a direct
     * partner iD.
     *
     * @returns {integer}
     */
    getDirectPartnerID: function () {
        return this._directPartnerID;
    },
    /**
     * @override
     */
    getPreview: function () {
        var result = this._super.apply(this, arguments);
        result.imageSRC = '/web/image/res.partner/' + this.getDirectPartnerID() + '/image_small';
        return result;
    },
    /**
     * @returns {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * DM are chat
     *
     * @override
     * @returns {boolean}
     */
    isChat: function () {
        return true;
    },
    /**
     * @param {string} newStatus
     */
    setStatus: function (newStatus) {
        this._status = newStatus;
    },
    /**
     * Unpin this DM
     *
     * @override
     * @return {$.Promise} resolve when unpinned
     */
    unsubscribe: function () {
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_pin',
            args: [this.getUUID(), false],
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

});

return DM;

});
