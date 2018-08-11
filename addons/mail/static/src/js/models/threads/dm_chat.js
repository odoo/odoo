odoo.define('mail.model.DMChat', function (require) {
"use strict";

var TwoUserChannel = require('mail.model.TwoUserChannel');

/**
 * Any piece of code in JS that make use of DMs must ideally interact with
 * such objects, instead of direct data from the server.
 */
var DMChat = TwoUserChannel.extend({
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {Object[]} params.data.direct_partner
     * @param {integer} params.data.direct_partner[0].id
     * @param {string} params.data.direct_partner[0].im_status
     * @param {string} params.data.direct_partner[0].name
     */
    init: function (params) {
        this._super.apply(this, arguments);

        var data = params.data;

        this._directPartnerID = data.direct_partner[0].id;
        this._name = data.direct_partner[0].name;
        this._status = data.direct_partner[0].im_status;
        this._type = 'dm_chat';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the direct partner ID linked to the DM, i.e. the partner ID of the
     * user at the other end of the DM conversation. All DM chats do have a
     * direct partner iD.
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
     * @param {string} newStatus
     */
    setStatus: function (newStatus) {
        this._status = newStatus;
    },
});

return DMChat;

});
