odoo.define('mail.model.ChannelSeenMixin', function (require) {
"use strict";

var session = require('web.session');

/**
 * Mixin for enabling the "seen" feature on channels.
 */
var ChannelSeenMixin = {
    /**
     * Initialize the internal data for seen feature on channels.
     *
     * Also listens on some internal events of the channel:
     *
     * - 'message_added': used to notify channel has been fetched
     *
     * @param {Object} params
     * @param {Object[]} [params.data.partners_info=[]]
     * @param {integer} [params.data.seen_partners_info[i].partner_id]
     * @param {integer|boolean} [params.data.seen_partners_info[i].fetched_message_id=false]
     * @param {integer|boolean} [params.data.seen_partners_info[i].seen_message_id=false]
     */
    init: function (params) {
        this._seenPartnersInfo = params.data.seen_partners_info || [];

        this.on('message_added', this, this._onSeenMessageAdded);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get list of members that have fetched the provided message on this
     * channel, but not yet seen it. Ignore current user in this list.
     *
     * @param {mail.model.Message} message
     * @returns {Object[]} list of members
     */
    getFetchedNotSeenMembers: function (message) {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });

        // seen partner IDs
        var seenPartnersInfo = _.filter(otherPartnersInfo, function (info) {
            return info.seen_message_id && info.seen_message_id >= message.getID();
        });
        var seenPartnerIDs = _.map(seenPartnersInfo, function (info) {
            return info.partner_id;
        });

        // fetched partner IDs (ignore seen)
        var fetchedPartnersInfo = _.filter(otherPartnersInfo, function (info) {
            var lastFetchedID = info.fetched_message_id || info.seen_message_id || 0;
            return lastFetchedID >= message.getID();
        });
        var fetchedPartnerIDs = _.map(fetchedPartnersInfo, function (info) {
            return info.partner_id;
        });
        fetchedPartnerIDs = _.reject(fetchedPartnerIDs, function (fetchedPartnerID) {
            return _.contains(seenPartnerIDs, fetchedPartnerID);
        });

        // fetched members
        var fetchedMembers = _.filter(this._members, function (member) {
            return _.contains(fetchedPartnerIDs, member.id);
        });

        return fetchedMembers;
    },
    /**
     * @returns {integer}
     */
    getLastMessageIDSeenByEveryone: function () {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });
        var seenMessageIDs = _.map(otherPartnersInfo, function (info) {
            return info.seen_message_id || 0;
        });
        if (_.isEmpty(seenMessageIDs)) {
            return 0;
        }
        return _.min(seenMessageIDs);
    },
    /**
     * Get list of members that have seen the provided message on this channel.
     * Ignore current user in this list.
     *
     * @param {mail.model.Message} message
     * @returns {Object[]} list of members
     */
    getSeenMembers: function (message) {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });

        // seen partner IDs
        var seenPartnersInfo = _.filter(otherPartnersInfo, function (info) {
            return info.seen_message_id >= message.getID();
        });
        var seenPartnerIDs = _.map(seenPartnersInfo, function (info) {
            return info.partner_id;
        });

        // seen members
        var seenMembers = _.filter(this._members, function (member) {
            return _.contains(seenPartnerIDs, member.id);
        });

        return seenMembers;
    },
    /**
     * @param {mail.model.Message} message
     * @returns {boolean}
     */
    hasEveryoneFetched: function (message) {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });
        var lastFetchedMessageIDs = _.map(otherPartnersInfo, function (info) {
            return info.fetched_message_id || info.seen_message_id || 0;
        });
        if (_.isEmpty(lastFetchedMessageIDs)) {
            return 0;
        }
        return message.getID() <= _.min(lastFetchedMessageIDs);
    },
    /**
     * @param {mail.model.Message} message
     * @returns {boolean}
     */
    hasEveryoneSeen: function (message) {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });
        var lastSeenMessageIDs = _.map(otherPartnersInfo, function (info) {
            return info.seen_message_id || 0;
        });
        if (_.isEmpty(lastSeenMessageIDs)) {
            return 0;
        }
        return message.getID() <= _.min(lastSeenMessageIDs);
    },
    /**
     * @param {mail.model.Message} message
     * @returns {boolean}
     */
    hasSomeoneFetched: function (message) {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });
        var lastFetchedMessageIDs = _.map(otherPartnersInfo, function (info) {
            return info.fetched_message_id || info.seen_message_id || 0;
        });
        if (_.isEmpty(lastFetchedMessageIDs)) {
            return false;
        }
        var fetched = _.find(lastFetchedMessageIDs, function (msgID) {
            return msgID >= message.getID();
        });
        return fetched;
    },
    /**
     * @param {mail.model.Message} message
     * @returns {boolean}
     */
    hasSomeoneSeen: function (message) {
        var otherPartnersInfo = _.filter(this._seenPartnersInfo, function (info) {
            return info.partner_id !== session.partner_id;
        });
        var lastSeenMessageIDs = _.map(otherPartnersInfo, function (info) {
            return info.seen_message_id || 0;
        });
        if (_.isEmpty(lastSeenMessageIDs)) {
            return false;
        }
        var seen = _.find(lastSeenMessageIDs, function (msgID) {
            return msgID >= message.getID();
        });
        return seen;
    },
    /**
     * @returns {boolean}
     */
    hasSeenFeature: function () {
        return true;
    },
    /**
     * @param {Object} data
     * @param {string} data.info either 'channel_seen' or 'channel_fetched'
     * @param {integer} data.partner_id
     * @param {integer} data.last_message_id
     */
    updateSeenPartnersInfo: function (data) {
        var seenInfo = _.findWhere(this._seenPartnersInfo, { partner_id: data.partner_id });
        if (!seenInfo) {
            seenInfo = {
                partner_id: data.partner_id,
                seen_message_id: 0,
                fetched_message_id: 0,
            };
            this._seenPartnersInfo.push(seenInfo);
        }
        if (data.info === 'channel_fetched') {
            seenInfo.fetched_message_id = data.last_message_id;
        } else if (data.info === 'channel_seen') {
            seenInfo.fetched_message_id = data.last_message_id;
            seenInfo.seen_message_id = data.last_message_id;
        }
        this.call('mail_service', 'getMailBus').trigger('update_channel', this.getID());
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSeenMessageAdded: function () {
        this.call('mail_service', 'notifyChannelFetched', { channelID: this._id });
    },
};

return ChannelSeenMixin;

});
