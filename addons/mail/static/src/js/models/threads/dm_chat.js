odoo.define('mail.model.DMChat', function (require) {
"use strict";

var ChannelSeenMixin = require('mail.model.ChannelSeenMixin');
var TwoUserChannel = require('mail.model.TwoUserChannel');

var core = require('web.core');

var _t = core._t;

/**
 * Any piece of code in JS that make use of DMs must ideally interact with
 * such objects, instead of direct data from the server.
 */
var DMChat = TwoUserChannel.extend(ChannelSeenMixin, {
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {string|undefined} [params.custom_channel_name] if set, use this
     *   custom name for this DM
     * @param {Object[]} params.data.direct_partner
     * @param {integer} params.data.direct_partner[0].id
     * @param {string} params.data.direct_partner[0].im_status
     * @param {string} params.data.direct_partner[0].name
     * @param {string} [params.data.direct_partner[0].out_of_office_message]
     * @param {string} [params.data.direct_partner[0].out_of_office_date_end]
     */
    init: function (params) {
        this._super.apply(this, arguments);
        ChannelSeenMixin.init.apply(this, arguments);

        var data = params.data;

        this._directPartnerID = data.direct_partner[0].id;
        this._name = data.custom_channel_name || data.direct_partner[0].name;
        this._outOfOfficeMessage = data.direct_partner[0].out_of_office_message;
        this._outOfOfficeDateEnd = data.direct_partner[0].out_of_office_date_end;
        this._type = 'dm_chat';

        this.call('mail_service', 'updateImStatus', [{
            id: this._directPartnerID,
            im_status: data.direct_partner[0].im_status
        }]);
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
    * Get the out of office info
    *
    * @override {mail.model.AbstractThread}
    * @returns {string|undefined}
    */
    getOutOfOfficeInfo: function () {
        if (!this._outOfOfficeDateEnd) {
            return undefined;
        }
        var currentDate = new Date();
        var date = new Date(this._outOfOfficeDateEnd);
        var options = { day: 'numeric', month: 'short' };
        if (currentDate.getFullYear() !== date.getFullYear()) {
            options.year = 'numeric';
        }
        var formattedDate = date.toLocaleDateString(window.navigator.language, options);
        return _.str.sprintf(_t("Out of office until %s"), formattedDate);
    },
    /**
    * Get the out of office message of the thread
    *
    * @override {mail.model.AbstractThread}
    * @returns {string}
    */
   getOutOfOfficeMessage: function () {
        return this._outOfOfficeMessage;
    },
    /**
     * @override
     */
    getPreview: function () {
        var result = this._super.apply(this, arguments);
        result.imageSRC = '/web/image/res.partner/' + this.getDirectPartnerID() + '/image_128';
        return result;
    },
    /**
     * @override
     * @return {string}
     */
    getStatus: function () {
        return this.call('mail_service', 'getImStatus', { partnerID: this._directPartnerID });
    },

    /**
     * @param {Object} data
     * @param {string} data.outOfOfficeMessage
     * @param {string} data.outOfOfficeDateEnd
     */
    updateOutOfOfficeInfo: function (data) {
        this._outOfOfficeMessage = data.outOfOfficeMessage;
        this._outOfOfficeDateEnd = data.outOfOfficeDateEnd;
        this.call('mail_service', 'getMailBus').trigger('updated_out_of_office', {
            threadID: this.getID(),
        });
    }
});

return DMChat;

});
