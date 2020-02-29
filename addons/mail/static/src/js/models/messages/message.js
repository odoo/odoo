odoo.define('mail.model.Message', function (require) {
"use strict";

var emojis = require('mail.emojis');
var AbstractMessage = require('mail.model.AbstractMessage');
var mailUtils = require('mail.utils');

var core = require('web.core');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var session = require('web.session');

var _t = core._t;

/**
 * This is the main class for the modeling messages in JS.
 * Such messages are stored in the mail manager, and any piece of JS code whose
 * logic relies on threads must ideally interact with such objects.
 */
var Message =  AbstractMessage.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @override
     * @param {web.Manager} parent
     * @param {Object} data
     * @param {string} [data.body = ""]
     * @param {(string|integer)[]} [data.channel_ids]
     * @param {Object[]} [data.customer_email_data]
     * @param {string} [data.customer_email_status]
     * @param {string} [data.email_from]
     * @param {string} [data.info]
     * @param {string} [data.model]
     * @param {string} [data.moderation_status='accepted']
     * @param {string} [data.module_icon]
     * @param {Array} [data.needaction_partner_ids = []]
     * @param {Array} [data.history_partner_ids = []]
     * @param {string} [data.record_name]
     * @param {integer} [data.res_id]
     * @param {Array} [data.starred_partner_ids = []]
     * @param {string} [data.subject]
     * @param {string} [data.subtype_description]
     * @param {Object[]} [data.tracking_value_ids]
     * @param {Object[]} emojis
     */
    init: function (parent, data, emojis) {
        this._super.apply(this, arguments);

        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        this._setInitialData(data);

        this._processBody(emojis);
        this._processMailboxes();
        this._processModeration();
        this._processDocumentThread();
        this._processTrackingValues();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} data
     */
    addCustomerEmailData: function (data) {
        this._customerEmailData.push(data);
    },
    /**
     * @override
     * @return {string|undefined}
     */
    getAuthorImStatus: function () {
        if (!this.hasAuthor()) {
            return undefined;
        }
        return this.call('mail_service', 'getImStatus', { partnerID: this.getAuthorID() });
    },
    /**
     * Get the name of the author of this message
     * If there are no author, return "".
     *
     * @return {string}
     */
    getAuthorName: function () {
        return this._getAuthorName();
    },
    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @override
     * @return {string}
     */
    getAvatarSource: function () {
        if (this._isOdoobotAuthor()) {
            return '/mail/static/src/img/odoobot.png';
        } else if (this.hasAuthor()) {
            return '/web/image/res.partner/' + this.getAuthorID() + '/image_128';
        } else if (this.getType() === 'email') {
            return '/mail/static/src/img/email_icon.png';
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    },
    /**
     * Get the customer email data of this email, if any.
     * If this message has no such data, returns 'undefined'
     *
     * @return {Object[]|undefined}
     */
    getCustomerEmailData: function () {
        if (!this.hasCustomerEmailData()) {
            return undefined;
        }
        return this._customerEmailData;
    },
    /**
     * Get the customer email status of this email, if any.
     * If this message has no such data, returns 'undefined'
     *
     * @return {string|undefined}
     */
    getCustomerEmailStatus: function () {
        if (!this.hasCustomerEmailData()) {
            return undefined;
        }
        return this._customerEmailStatus;
    },
    /**
     * Get the text to display for the author of the message
     *
     * Rule of precedence for the displayed author::
     *
     *      author name > sender email > "anonymous"
     *
     * @override
     * @return {string}
     */
    getDisplayedAuthor: function () {
        var res = this._super.apply(this, arguments);
        if (res) {
            return res;
        } else {
            return  this.hasEmailFrom() ? this.getEmailFrom() :
                _t("Anonymous");
        }
    },
    /**
     * Get the ID of the document that this message is linked.
     *
     * @override
     * @return {integer}
     */
    getDocumentID: function () {
        return this._documentID;
    },
    /**
     * Get the model of the document that this message is linked.
     * If this message is not linked to a document, returns "".
     *
     * @override
     * @return {string}
     */
    getDocumentModel: function () {
        return this._documentModel;
    },
    /**
     * Get the name of the document that this message is linked.
     * If this message is not linked to a document, returns "".
     *
     * It uses the name of an existing document thread, in order to have the
     * updated document name. If there is no document thread yet, use the
     * currently aware document name.
     *
     * As a result, this method should ideally be called internally, in order
     * to avoid having different names for messages linked to a same modified
     * document.
     *
     * @override
     * @return {string}
     */
    getDocumentName: function () {
        if (!this.isLinkedToDocumentThread()) {
            return "";
        }
        var model = this.getDocumentModel();
        var id = this.getDocumentID();
        var documentThread = this.call('mail_service', 'getDocumentThread', model, id);
        if (documentThread) {
            this._documentName = documentThread.getName();
        }
        return this._documentName;
    },
    /**
     * Get the email of the sender of this message.
     * If this email has no sender email, returns "".
     *
     * @return {string}
     */
    getEmailFrom: function () {
        if (!this.hasEmailFrom()) {
            return "";
        }
        return this._emailFrom;
    },
    /**
     * Get the ID of the channel that this message originates from.
     * If this message does not originate from a channel, returns `-1`.
     *
     * @override
     * @return {integer}
     */
    getOriginChannelID: function () {
        if (!this.originatesFromChannel()) {
            return -1;
        }
        return this._documentID;
    },
    /**
     * Get the name of the channel that this message originates from.
     * If this message does not originate from a channel, returns "".
     *
     * @override
     * @returns {string}
     */
    getOriginChannelName: function () {
        if (!this.originatesFromChannel()) {
            return "";
        }
        var originChannelID = this.getOriginChannelID();
        var channel = originChannelID && this.call(
                                            'mail_service',
                                            'getChannel',
                                            originChannelID);
        if (!channel) {
            return "";
        }
        return channel.getName();
    },
    /**
     * Returns the information required to render the preview of this channel.
     *
     * @return {Object}
     */
    getPreview: function () {
        var id, title;
        if (this.isLinkedToDocumentThread()) {
            id = this.getDocumentModel() + '_' + this.getDocumentID();
            title = this.getDocumentName();
        } else {
            id = 'mailbox_inbox';
            title = this.hasSubject() ? this.getSubject() : this.getDisplayedAuthor();
        }
        return {
            author: this.getDisplayedAuthor(),
            body: mailUtils.htmlToTextContentInline(this.getBody()),
            date: this.getDate(),
            documentModel: this.getDocumentModel(),
            documentID: this.getDocumentID(),
            id: id,
            imageSRC: this._getModuleIcon() || this.getAvatarSource(),
            messageID: this.getID(),
            status: this.status,
            title: title,
            isLinkedToDocumentThread: this.isLinkedToDocumentThread(),
        };
    },
    /**
     * Get the subject of this message
     * If this message has no subject, returns "".
     *
     * @override
     * @return {string}
     */
    getSubject: function () {
        if (!this.hasSubject()) {
            return "";
        }
        return this._subject;
    },
    /**
     * @override
     * @return {string}
     */
    getSubtypeDescription: function () {
        return this._subtypeDescription;
    },
    /**
     * Get the list of thread IDs that this message is linked to
     * If this message is not linked to a thread, returns 'undefined'
     *
     * @return {string[]|undefined} list of thread IDs, if any
     */
    getThreadIDs: function () {
        return this._threadIDs;
    },
    /**
     * Get the tracking values of this message
     * If this message has no tracking values, returns 'undefined'
     *
     * @override
     * @return {Object[]|undefined}
     */
    getTrackingValues: function () {
        if (!this.hasTrackingValues()) {
            return undefined;
        }
        return this._trackingValueIDs;
    },
    /**
     * @override
     * @return {string}
     */
    getURL: function () {
        return session.url('/mail/view?message_id=' + this._id);
    },
    /**
     * State whether this message contains some customer email data
     *
     * @override
     * @return {boolean}
     */
    hasCustomerEmailData: function () {
        return !!(this._customerEmailData && (this._customerEmailData.length > 0));
    },
    /**
     * State whether this message has an email of its sender.
     *
     * @override
     * @return {string}
     */
    hasEmailFrom: function () {
        return !!(this._emailFrom);
    },
    /**
     * State whether this message has a subject
     *
     * @return {boolean}
     */
    hasSubject: function () {
        return !!(this._subject);
    },
    /**
     * @override
     * @return {boolean}
     */
    hasSubtypeDescription: function () {
        return !!(this._subtypeDescription);
    },
    /**
     * State whether this message contains some tracking values
     *
     * @override
     * @return {boolean}
     */
    hasTrackingValues: function () {
        return !!(this._trackingValueIDs && (this._trackingValueIDs.length > 0));
    },
    /**
     * State whether this message is linked to a document thread (not channel)
     *
     * Usually, if this is true, then this message comes from a document thread,
     * but the document model could be a channel. In that case, the document
     * resID tells the channel that this message originally comes from.
     *
     * To detect whether the message comes from a channel, see the method
     * 'originatesFromChannel'.
     *
     * @override
     * @return {boolean}
     */
    isLinkedToDocumentThread: function () {
        return !!(this._documentModel !== 'mail.channel' && this._documentID && this._type !== 'user_notification');
    },
    /**
     * State whether the current user is the author of this message
     *
     * @return {boolean}
     */
    isMyselfAuthor: function () {
        return this._isMyselfAuthor();
    },
    /**
     * States whether the current message needs moderation in general.
     *
     * @override
     * @returns {boolean}
     */
    needsModeration: function () {
        return this._moderationStatus === 'pending_moderation';
    },
    /**
     * States whether the current message needs moderation by the current user.
     * Such a message should be in the moderation mailbox.
     *
     * @returns {boolean}
     */
    needsModerationByUser: function () {
        return _.contains(this._threadIDs, 'mailbox_moderation');
    },
    /**
     * State whether this message is needaction
     *
     * @override
     * @returns {boolean}
     */
    isNeedaction: function () {
        return _.contains(this._threadIDs, 'mailbox_inbox');
    },
    /**
     * State whether this message is starred
     *
     * @override
     * @returns {boolean}
     */
    isStarred: function () {
        return _.contains(this._threadIDs, 'mailbox_starred');
    },
    /**
     * State whether this message is a system notification
     *
     * @override
     * @returns {boolean}
     */
    isSystemNotification: function () {
        return (
                this.getType() === 'notification' &&
                this._documentModel === 'mail.channel'
            ) || this._isTransient();
    },
    /**
     * States whether the message originates from a channel or not
     *
     * @returns {boolean}
     */
    originatesFromChannel: function () {
        return this._documentModel === 'mail.channel';
    },
    /**
     * Unregister thread with ID `threadID` from this message
     *
     * @param {string|integer} threadID ID of thread
     */
    removeThread: function (threadID) {
        this._threadIDs = _.without(this._threadIDs, threadID);
    },
    /**
     * Update the moderation status of the message, so that it is now accepted
     * or rejected. When the message is accepted, it may be linked to more
     * threads, which is the case for relay channels on moderated channels.
     *
     * @param {string} newModerationStatus ['accepted', 'rejected']
     * @param {Object} [options]
     * @param {Object} [options.additionalThreadIDs] contains additional thread
     *   IDs to be registered on the message.
     */
    setModerationStatus: function (newModerationStatus, options) {
        var self = this;
        if (newModerationStatus === this._moderationStatus) {
            return;
        }
        this._moderationStatus = newModerationStatus;
        if (newModerationStatus === 'accepted' && options) {
            _.each(options.additionalThreadIDs, function (threadID) {
                self._addThread(threadID);
            });
        }
        this._warnMessageModerated();
    },
    /**
     * Set whether the message is starred or not.
     * If it is starred, the message is moved to the "Starred" mailbox.
     * Note that this function only applies it locally, the server is not aware
     *
     * @param {boolean} starred if set, the message is starred
     */
    setStarred: function (starred) {
        if (starred) {
            this._addThread('mailbox_starred');
        } else {
            this.removeThread('mailbox_starred');
        }
    },
    /**
     * State whether this message should display the subject
     *
     * @return {boolean}
     */
    shouldDisplaySubject: function () {
        return this.hasSubject() &&
                this.getType() !== 'notification' &&
                !this.originatesFromChannel();
    },
    /**
     * State whether this message should redirect to the author
     * when clicking on the author of this message.
     *
     * Do not redirect on author clicked of self-posted or Odoobot messages
     * (note: Odoobot is the default author of transient messages)
     *
     * @override
     * @return {boolean}
     */
    shouldRedirectToAuthor: function () {
        return this._super.apply(this, arguments) && !this._isOdoobotAuthor();
    },
    /**
     * Toggle the star status of the message
     *
     * It relies on the star status of the message from the date of the server.
     * The star status is updated from a 'toggle_star' notification on the
     * longpoll bus
     *
     * @see {mail.Manager.Notification} for the receipt of 'toggle_star'
     *   notification after this rpc.
     *
     * @return {Promise}
     */
    toggleStarStatus: function () {
        return this._rpc({
                model: 'mail.message',
                method: 'toggle_message_starred',
                args: [[this._id]],
            });
    },
    /**
     * Update the customer email status
     *
     * @param {string} newCustomerEmailStatus
     */
    updateCustomerEmailStatus: function (newCustomerEmailStatus) {
        this._customerEmailStatus = newCustomerEmailStatus;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Register a thread to the message
     * Useful when you mark a message as 'to do'.
     * This message will be available in 'Starred' mailbox.
     *
     * @private
     * @param  {string|integer} threadID
     */
    _addThread: function (threadID) {
        if (!this._threadIDs) {
            this._threadIDs = [];
        }
        this._threadIDs.push(threadID);
        this._threadIDs = _.uniq(this._threadIDs);
    },
    /**
     * Get the name of the author of this message.
     * If Odoobot is the author (default author for transient messages),
     * returns 'Odoobot'.
     *
     * @override
     * @private
     * @returns {string}
     */
    _getAuthorName: function () {
        if (this._isOdoobotAuthor()) {
            return "OdooBot";
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @return {string}
     */
    _getModuleIcon: function () {
        return this._moduleIcon;
    },
    /**
     * State if the author of this message is OdooBot
     * This is the default author for transient messages.
     *
     * @private
     * @return {boolean}
     */
    _isOdoobotAuthor: function () {
        return this._serverAuthorID &&
            this._serverAuthorID[0] === this.call('mail_service', 'getOdoobotID')[0];
    },
    /**
     * State whether the message is transient or not
     *
     * @private
     * @return {boolean}
     */
    _isTransient: function () {
        return this._info === 'transient_message';
    },
    /**
     * Convert the server-format body of the message to the client-format.
     * Basically, it processes emojis and url.
     *
     * @private
     */
    _processBody: function () {
        var self = this;

        _.each(emojis, function (emoji) {
            var unicode = emoji.unicode;
            var regexp = new RegExp("(?:^|\\s|<[a-z]*>)(" + unicode + ")(?=\\s|$|</[a-z]*>)", 'g');
            var originalBody = self._body;
            self._body = self._body.replace(regexp,
                ' <span class="o_mail_emoji">' + unicode + '</span> ');
            // Idiot-proof limit. If the user had the amazing idea of
            // copy-pasting thousands of emojis, the image rendering can lead
            // to memory overflow errors on some browsers (e.g. Chrome). Set an
            // arbitrary limit to 200 from which we simply don't replace them
            // (anyway, they are already replaced by the unicode counterpart).
            if (_.str.count(self._body, 'o_mail_emoji') > 200) {
                self._body = originalBody;
            }
        });

        // add anchor tags to urls
        self._body = mailUtils.parseAndTransform(self._body, mailUtils.addLink);
    },
    /**
     * If the message is linked to a document, link this message to the related
     * document thread. If there is no document thread yet, create it
     */
    _processDocumentThread: function () {
        if (!this.isLinkedToDocumentThread()) {
            return;
        }
        var resModel = this.getDocumentModel();
        var resID = this.getDocumentID();
        var documentThread = this.call('mail_service', 'getOrAddDocumentThread', {
                resModel: resModel,
                resID: resID,
                name: this.getDocumentName(),
            });
        this._threadIDs.push(documentThread.getID());
    },
    /**
     * Set the appropriate mailboxes to this message based on server data
     *
     * @private
     */
    _processMailboxes: function () {
        if (_.contains(this._needactionPartnerIDs, session.partner_id)) {
            this._setNeedaction(true);
        }
        if (_.contains(this._starredPartnerIDs, session.partner_id)) {
            this.setStarred(true);
        }
        if (_.contains(this._historyPartnerIDs, session.partner_id)) {
            this._setHistory(true);
        }
        if (
            this.originatesFromChannel() &&
            _.contains(
                this.call('mail_service', 'getModeratedChannelIDs'),
                this.getOriginChannelID()
            ) &&
            this.needsModeration()
        ) {
            this._setModeratedByUser(true);
        }
    },
    /**
     * Do some extra processing at message init, related to the
     * moderated status of the message.
     *
     * If the message needs moderation, it is not yet linked to the
     * moderated channel server-side. Therefore, it is not registered
     * in the list of threadIDs, as it is built on server-side information
     * at message initialisation (using data.channel_ids).
     *
     * Since the web client uses the list of thread IDs to show visually the
     * message in a thread, we should hack the response of the server so that
     * it assumes the message really belongs to this thread.
     *
     * @private
     */
    _processModeration: function () {
        if (this.needsModeration()) {
            // the message is not linked to the moderated channel on the
            // server, therefore this message has not this channel in
            // channel_ids. Here, just to show this message in the channel
            // visually, it links this message to the channel
            this._threadIDs.push(this.getOriginChannelID());
        }
    },
    /**
     * Process the tracking values on message creation, which
     * basically format date to the local only once by message
     *
     * Cannot be done in preprocess, since it alter the original value
     *
     * @private
     */
    _processTrackingValues: function () {
        if (this.hasTrackingValues()) {
            _.each(this.getTrackingValues(), function (trackingValue) {
                if (trackingValue.field_type === 'datetime') {
                    if (trackingValue.old_value) {
                        trackingValue.old_value =
                            moment
                                .utc(trackingValue.old_value)
                                .local()
                                .format('LLL');
                    }
                    if (trackingValue.new_value) {
                        trackingValue.new_value =
                            moment
                                .utc(trackingValue.new_value)
                                .local()
                                .format('LLL');
                    }
                } else if (trackingValue.field_type === 'date') {
                    if (trackingValue.old_value) {
                        trackingValue.old_value =
                            moment(trackingValue.old_value)
                                .local()
                                .format('LL');
                    }
                    if (trackingValue.new_value) {
                        trackingValue.new_value =
                            moment(trackingValue.new_value)
                                .local()
                                .format('LL');
                    }
                }
            });
        }
    },
    /**
     * @private
     * @param {Object} data
     * @param {string} [data.body = ""]
     * @param {(string|integer)[]} [data.channel_ids]
     * @param {Object[]} [data.customer_email_data]
     * @param {string} [data.customer_email_status]
     * @param {string} [data.email_from]
     * @param {string} [data.info]
     * @param {string} [data.model]
     * @param {string} [data.moderation_status='accepted']
     * @param {string} [data.module_icon]
     * @param {Array} [data.needaction_partner_ids = []]
     * @param {Array} [data.history_partner_ids = []]
     * @param {string} [data.record_name]
     * @param {integer} [data.res_id]
     * @param {Array} [data.starred_partner_ids = []]
     * @param {string} [data.subject]
     * @param {string} [data.subtype_description]
     * @param {Object[]} [data.tracking_value_ids]
     */
    _setInitialData: function (data){
        this._customerEmailData = data.customer_email_data || [];
        this._customerEmailStatus = data.customer_email_status;
        this._documentModel = data.model;
        this._documentName = data.record_name;
        this._documentID = data.res_id;
        this._emailFrom = data.email_from;
        this._info = data.info;
        this._isNote = data.is_note;
        this._moduleIcon = data.module_icon;
        this._needactionPartnerIDs = data.needaction_partner_ids || [];
        this._starredPartnerIDs = data.starred_partner_ids || [];
        this._historyPartnerIDs = data.history_partner_ids || [];
        this._subject = data.subject;
        this._subtypeDescription = data.subtype_description;
        this._threadIDs = data.channel_ids || [];
        this._trackingValueIDs = data.tracking_value_ids;

        this._moderationStatus = data.moderation_status || 'accepted';
    },
    /*
     * Set whether the message is history or not.
     * If it is history, the message is moved to the "History" mailbox.
     * Note that this function only applies it locally, the server is not aware
     *
     * @private
     * @param {boolean} history if set, the message is history
     */
    _setHistory: function (history) {
        if (history) {
            this._addThread('mailbox_history');
        } else {
            this.removeThread('mailbox_history');
        }
    },
    /**
     * Set whether the message is moderated by current user or not.
     * If it is moderated by the current user, the message is moved to the
     * "Moderation" mailbox. Note that this function only applies it locally,
     * the server is not aware
     *
     * @private
     * @param {boolean} moderated if set, the message is moderated by user
     */
    _setModeratedByUser: function (moderated) {
        if (moderated) {
            this._addThread('mailbox_moderation');
        } else {
            this.removeThread('mailbox_moderation');
        }
    },
    /**
     * Set whether the message is needaction or not.
     * If it is needaction, the message is moved to the "Inbox" mailbox.
     * Note that this function only applies it locally, the server is not aware
     *
     * @private
     * @param {boolean} needaction if set, the message is needaction
     */
    _setNeedaction: function (needaction) {
        if (needaction) {
            this._addThread('mailbox_inbox');
        } else {
            this.removeThread('mailbox_inbox');
        }
    },
    /**
     * @private
     */
    _warnMessageModerated: function () {
        var mailBus = this.call('mail_service', 'getMailBus');
        if (this.needsModerationByUser()) {
            this._setModeratedByUser(false);
            var moderationBox = this.call('mail_service', 'getMailbox', 'moderation');
            moderationBox.decrementMailboxCounter();
            moderationBox.removeMessage(this.getID());
            mailBus.trigger('update_moderation_counter');
        }
        if (this._moderationStatus !== 'accepted') {
            this.call('mail_service', 'removeMessageFromThreads', this);
        }
        mailBus.trigger('update_message', this);
    },

});

return Message;

});
