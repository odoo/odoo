odoo.define('mail.Manager.Status', function (require) {
"use strict";

var core = require('web.core');
var MailManager = require('mail.Manager');
var mailUtils = require('mail.utils');
var QWeb = core.qweb;

/**
 * Mail Manager: IM Status
 *
 * This component handles im status of partners, which is useful for DM Chats,
 * partner mention suggestions, and chatter messages that display the user icon.
 */
MailManager.include({
    _UPDATE_INTERVAL: 50,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the uin cache im status, and triggers an asynchronous throttled
     * update of im_status cache for missings
     *
     * @param {Object} data
     * @param {integer} data.partnerID
     * @return {String}
     */
    getImStatus: function (data) {
        var self = this;
        var partnerID = data.partnerID;
        if (partnerID === this.getOdoobotID()[0]) {
            return 'bot';
        }
        if (!this._imStatus[partnerID]) {
            // Add to list to call it in next bus update or _fetchMissingImStatus
            this._imStatus[partnerID] = undefined;
            // fetch after some time if no other getImStatus occurs
            mailUtils.clearTimeout(this._fetchStatusTimeout);
            this._fetchStatusTimeout = mailUtils.setTimeout(function () {
                self._fetchMissingImStatus();
            }, 500);
        }
        return this._imStatus[partnerID];
    },
    /**
     * Update status manually, to avoid to do a rpc and an asynchronous update
     * after getImStatus. Can be done by any caller knowing the last im_status
     * state.
     *
     * @param {Object[]} statusList, A list of {id, im_status}
     */
    updateImStatus: function (statusList) {
        var updatedIDs = [];
        var self = this;
        var dmChat;
        var toUpdateOutOfOfficeChatIDs = [];
        _.each(statusList, function (status) {
            if (self._imStatus[status.id] === status.im_status) {
                return;
            }
            if (
                status.im_status.indexOf('leave') !== -1 ||
                (
                    self._imStatus[status.id] &&
                    self._imStatus[status.id].indexOf('leave') !== -1
                )
            ) {
                dmChat = self.getDMChatFromPartnerID(status.id);
                if (dmChat) {
                    toUpdateOutOfOfficeChatIDs.push(dmChat.getID());
                }
            }
            updatedIDs.push(status.id);
            self._imStatus[status.id] = status.im_status;
        });
        if (!_.isEmpty(toUpdateOutOfOfficeChatIDs)) {
            this._rpc({
                model: 'mail.channel',
                method: 'channel_info',
                args: [toUpdateOutOfOfficeChatIDs],
            }).then(function (channelsInfo) {
                _.each(channelsInfo, function (channelInfo) {
                    dmChat = self.getChannel(channelInfo.id);
                    if (!dmChat) {
                        return;
                    }
                    dmChat.updateOutOfOfficeInfo({
                        outOfOfficeMessage: channelInfo.direct_partner[0].out_of_office_message,
                        outOfOfficeDateEnd: channelInfo.direct_partner[0].out_of_office_date_end,
                    });
                });
            });
        }
        if (! _.isEmpty(updatedIDs)) {
            this._mailBus.trigger('updated_im_status', updatedIDs); // useful for thread window header
            this._renderImStatus(updatedIDs);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch the list of im_status for partner with id in ids list and triggers
     * an update.
     *
     * @private
     * @param {Object} data
     * @param {integer[]} data.partnerIDs
     * @return {Deferred}
     */
    _fetchImStatus: function (data) {
        var self = this;
        var partnerIDs = data.partnerIDs;
        if (_.isEmpty(partnerIDs)) {
            return Promise.resolve();
        }
        return this._rpc({
            route: '/longpolling/im_status',
            params: { partner_ids: partnerIDs },
        }, {
            shadow: true,
        }).then( function (results) {
            self.updateImStatus(results);
        });
    },
    /**
     * Fetch the list of im_status for partner with an unknown im_status and
     * triggers an update.
     *
     * @private
     * @return {Deferred}
     */
    _fetchMissingImStatus: function () {
        var missing = [];
        _.each(this._imStatus, function (value, key) {
            if (value === undefined) {
                missing.push(Number(key));
            }
        });
        return this._fetchImStatus({ partnerIDs: missing });
    },
    /**
     * @private
     * @return {integer[]} a list of partner ids that needs update
     */
    _getImStatusToUpdate: function () {
        var toUpdate = [];
        _.each(this._imStatus, function (status, key) {
            //filter on im_partner and bot: useless to update them, status won't change
            if (['im_partner', 'bot'].indexOf(status) === -1) {
                toUpdate.push(Number(key));
            }
        });
        return toUpdate;
    },
    /**
     * @override
     * @private
     */
    _initializeInternalState: function () {
        this._super.apply(this, arguments);
        this._fetchStatusTimeout = undefined;
        this._imStatus = {};
        this._isTabFocused = true;
        this._updateImStatusLoop();
    },
    /**
     * @override
     * @private
     */
    _listenOnBuses: function () {
        this._super.apply(this, arguments);
        $(window).on("focus", this._onWindowFocusChange.bind(this, true));
        $(window).on("blur", this._onWindowFocusChange.bind(this, false));
        $(window).on("unload", this._onWindowFocusChange.bind(this, false));
    },
    /**
     * @private
     * @param {integer[]} updatedIds
     */
    _renderImStatus: function (updatedIds) {
        var self = this;
        $('.o_updatable_im_status').each(function () {
            var $this = $(this);
            var partnerID = $this.data('partner-id');
            if (partnerID !== undefined && updatedIds.indexOf(partnerID) !== -1) { // todo instead add id on o_updatable_im_status and select only concerned ones
                var status = QWeb.render('mail.UserStatus', {
                    status: self.getImStatus({ partnerID: partnerID }),
                    partnerID: partnerID,
                });
                $this.replaceWith(status);
            }
        });
    },
    /**
     * Once initialised, this loop will update the im_status of registered
     * users.
     *
     * @private
     * @param {integer} [counter=0] The recursion loop counter
     */
    _updateImStatusLoop: function (counter) {
        var self = this;
        if (!_.isNumber(counter)) {
            counter = 0;
        }
        mailUtils.setTimeout(function () {
            if (counter >= self._UPDATE_INTERVAL && self._isTabFocused) {
                self._fetchImStatus({ partnerIDs: self._getImStatusToUpdate() });
                counter = 0;
            }
            self._updateImStatusLoop(counter+1);
        }, 1000);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {boolean} focused
     */
    _onWindowFocusChange: function (focused) {
        this._isTabFocused = focused;
    },
});

});
