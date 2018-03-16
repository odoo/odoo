odoo.define('mail.model.Message', function (require) {
"use strict";

var MessagePreview = require('mail.model.MessagePreview');
var mailUtils = require('mail.utils');

var Class = require('web.Class');
var core = require('web.core');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var session = require('web.session');
var time = require('web.time');

var _t = core._t;

var ODOOBOT_ID = "ODOOBOT"; // default author_id for transient messages

var Message =  Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @override
     * @param {web.Widget} parent
     * @param {Object} data
     * @param {Object[]} [data.attachment_ids = []]
     * @param {Array} data.author_id
     * @param {string} [data.body = ""]
     * @param {(string|integer)[]} [data.channel_ids]
     * @param {Object[]} [data.customer_email_data]
     * @param {string} [data.customer_email_status]
     * @param {string} [data.date] the server-format date time of the message.
     *   If not provided, use current date time for this message.
     * @param {string} [data.email_from]
     * @param {integer} data.id
     * @param {string} [data.info]
     * @param {boolean} [data.is_discussion = false]
     * @param {boolean} [data.is_note = false]
     * @param {string} [data.message_type]
     * @param {string} [data.model]
     * @param {string} [data.module_icon]
     * @param {Array} [data.needaction_partner_ids = []]
     * @param {string} [data.record_name]
     * @param {integer} [data.res_id]
     * @param {Array} [data.starred_partner_ids = []]
     * @param {string} [data.subject]
     * @param {*} [data.subtype_description]
     * @param {Object[]} [data.tracking_value_ids]
     * @param {Object[]} emojis
     */
    init: function (parent, data, emojis) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        this._attachmentIDs = data.attachment_ids || [];
        this._body = data.body || "";
        this._conversationIDs = data.channel_ids;
        this._customerEmailData = data.customer_email_data;
        this._customerEmailStatus = data.customer_email_status;
        this._date = data.date ? moment(time.str_to_datetime(data.date)) : moment(); // by default: current datetime
        this._displayAuthor = false; // if set, the message should display the author of the message
        this._documentModel = data.model;
        this._documentName = data.record_name;
        this._documentResID = data.res_id;
        this._emailFrom = data.email_from;
        this._id = data.id;
        this._info = data.info;
        this._isDiscussion = data.is_discussion;
        this._isNote = data.is_note;
        this._moduleIcon = data.module_icon;
        this._needactionPartnerIDs = data.needaction_partner_ids || [];
        this._originChannelID = undefined;
        this._originChannelName = undefined;
        this._serverAuthorID = data.author_id;
        this._starredPartnerIDs = data.starred_partner_ids || [];
        this._subject = data.subject;
        this._subtypeDescription = data.subtype_description;
        this._trackingValueIDs = data.tracking_value_ids;
        this._type = data.message_type;

        this._processAttachmentURL();
        this._processBody(emojis);
        this._processMailboxes();
        this._processOriginChannel();
        this._processTrackingValues();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Set whether the message should display the author or not
     *
     * @param {boolean} bool if set, display the author of this message
     */
    displayAuthor: function (bool) {
        this._displayAuthor = bool;
    },
    /**
     * Get the list of files attached to this message.
     * Note that attachments are stored with server-format
     *
     * @return {Object[]}
     */
    getAttachments: function () {
        return this._attachmentIDs;
    },
    /**
     * Get the list of images attached to this message.
     * Note that attachments are stored with server-format
     *
     * @return {Object[]}
     */
    getImageAttachments: function () {
        return _.filter(this.getAttachments(), function (attachment) {
            return attachment.mimetype && attachment.mimetype.split('/')[0] === 'image';
        });
    },
    /**
     * Get the list of non-images attached to this message.
     * Note that attachments are stored with server-format
     *
     * @return {Object[]}
     */
    getNonImageAttachments: function () {
        return _.difference(this.getAttachments(), this.getImageAttachments());
    },
    /**
     * Get the server ID (number) of the author of this message
     * If there are no author, return -1;
     *
     * @return {integer}
     */
    getAuthorID: function () {
        if (!this.hasAuthor()) {
            return -1;
        }
        return this._serverAuthorID[0];
    },
    /**
     * Get the name of the author of this message
     * If there are no author, return "".
     *
     * @return {string}
     */
    getAuthorName: function () {
        if (!this.hasAuthor()) {
            return "";
        }
        if (this._isOdoobotAuthor()) {
            return "Odoobot";
        }
        return this._serverAuthorID[1];
    },
    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @return {string}
     */
    getAvatarSource: function () {
        if (this._isOdoobotAuthor()) {
            return '/mail/static/src/img/odoo_o.png';
        } else if (this.hasAuthor()) {
            return '/web/image/res.partner/' + this.getAuthorID() + '/image_small';
        } else if (this._type === 'email') {
            return '/mail/static/src/img/email_icon.png';
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    },
    /**
     * Get the body content of this message
     *
     * @return {string}
     */
    getBody: function () {
        return this._body;
    },
    /**
     * Get the list of conversation IDs that this message is linked to
     * If this message is not linked to a conversation, returns 'undefined'
     *
     * @return {string[]|undefined} list of conversation IDs, if any
     */
    getConversationIDs: function () {
        return this._conversationIDs;
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
     * @return {moment}
     */
    getDate: function () {
        return this._date;
    },
    /**
     * Get the date day of this message
     *
     * @return {string}
     */
    getDateDay: function () {
        var date = this.getDate().format('YYYY-MM-DD');
        if (date === moment().format('YYYY-MM-DD')) {
            return _t("Today");
        } else if (date === moment().subtract(1, 'days').format('YYYY-MM-DD')) {
            return _t("Yesterday");
        }
        return this.getDate().format('LL');
    },
    /**
     * Get the text to display for the author of the message
     *
     * Rule of precedence for the displayed author:
     *
     *      author name > sender email > "anonymous"
     *
     * @return {string}
     */
    getDisplayedAuthor: function () {
        return this.hasAuthor() ? this.getAuthorName() :
                this.hasEmailFrom() ? this.getEmailFrom() :
                _t("Anonymous");
    },
    /**
     * Get the model of the document that this message is linked.
     * If this message is not linked to a document, returns "".
     *
     * @return {string}
     */
    getDocumentModel: function () {
        if (!this.isLinkedToDocument()) {
            return "";
        }
        return this._documentModel;
    },
    /**
     * Get the name of the document that this message is linked.
     * If this message is not linked to a document, returns "".
     *
     * @return {string}
     */
    getDocumentName: function () {
        if (!this.isLinkedToDocument()) {
            return "";
        }
        return this._documentName;
    },
    /**
     * Get the ID of the document that this message is linked.
     * If this message is not linked to a document, returns -1.
     *
     * @return {integer}
     */
    getDocumentResID: function () {
        if (!this.isLinkedToDocument()) {
            return -1;
        }
        return this._documentResID;
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
     * Get the server ID (number) of this message
     *
     * @return {integer}
     */
    getID: function () {
        return this._id;
    },
    /**
     * @return {string}
     */
    getModuleIcon: function () {
        return this._moduleIcon;
    },
    /**
     * Get the ID of the channel that this message originates from.
     * If this message does not originate from a channel, returns `-1`.
     *
     * @return {integer}
     */
    getOriginChannelID: function () {
        if (!this.hasOriginChannel()) {
            return -1;
        }
        return this._originChannelID;
    },
    /**
     * Get the name of the channel that this message originates from.
     * If this message does not originate from a channel, returns "".
     */
    getOriginChannelName: function () {
        if (!this.hasOriginChannel()) {
            return "";
        }
        return this._originChannelName;
    },
    /**
     * Get preview of a message coming from inbox
     *
     * NOTE: this is a temporary function for retro-compatibility of chatter previews!
     *
     * @param {integer} unreadCounter the counter to display next to this message
     * @return {mail.model.MessagePreview} preview format of the message
     */
    getPreview: function (unreadCounter) {
        return new MessagePreview(this, unreadCounter);
    },
    /**
     * Get the subject of this message
     * If this message has no subject, returns "".
     *
     * @return {string}
     */
    getSubject: function () {
        if (!this.hasSubject()) {
            return "";
        }
        return this._subject;
    },
    /**
     * @return {string}
     */
    getSubtypeDescription: function () {
        return this._subtypeDescription;
    },
    /**
     * Get the time elapsed between sent message and now
     *
     * @return {string}
     */
    getTimeElapsed: function () {
        return mailUtils.timeFromNow(this.getDate());
    },
    /**
     * Get the tracking values of this message
     * If this message has no tracking values, returns 'undefined'
     *
     * @return {Object[]|undefined}
     */
    getTrackingValues: function () {
        if (!this.hasTrackingValues()) {
            return undefined;
        }
        return this._trackingValueIDs;
    },
    /**
     * Get the type of the message (e.g. 'comment', 'email', 'notification', ...)
     *
     * @return {string}
     */
    getType: function () {
        return this._type;
    },
    /**
     * @return {string}
     */
    getURL: function () {
        return session.url('/mail/view?message_id=' + this._id);
    },
    /**
     * State whether this message contains some attachments.
     *
     * @return {boolean}
     */
    hasAttachments: function () {
        return this._attachmentIDs.length > 0;
    },
    /**
     * State whether this message has an author
     *
     * @return {boolean}
     */
    hasAuthor: function () {
        return !!(this._serverAuthorID && this._serverAuthorID[0]);
    },
    /**
     * State whether this message contains some customer email data
     *
     * @return {boolean}
     */
    hasCustomerEmailData: function () {
        return !!(this._customerEmailData && (this._customerEmailData.length > 0));
    },
    /**
     * State whether this message has an email of its sender.
     *
     * @return {string}
     */
    hasEmailFrom: function () {
        return !!(this._emailFrom);
    },
    /**
     * State whether this image contains images attachments
     *
     * @return {boolean}
     */
    hasImageAttachments: function () {
        return _.some(this._attachmentIDs, function (attachment) {
            return attachment.mimetype && attachment.mimetype.split('/')[0] === 'image';
        });
    },
    /**
     * State whether this message originates from a channel.
     *
     * @return {boolean}
     */
    hasOriginChannel: function () {
        return !!this._originChannelID;
    },
    /**
     * State whether this image contains non-images attachments
     *
     * @return {boolean}
     */
    hasNonImageAttachments: function () {
        return _.some(this._attachmentIDs, function (attachment) {
            return !(attachment.mimetype && attachment.mimetype.split('/')[0] === 'image');
        });
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
     * @return {boolean}
     */
    hasSubtypeDescription: function () {
        return !!(this._subtypeDescription);
    },
    /**
     * State whether this message contains some tracking values
     *
     * @return {boolean}
     */
    hasTrackingValues: function () {
        return !!(this._trackingValueIDs && (this._trackingValueIDs.length > 0));
    },
    /**
     * State whether the current user is the author of this message
     *
     * @return {boolean}
     */
    isAuthor: function () {
        return this.hasAuthor() && (this.getAuthorID() === session.partner_id);
    },
    /**
     * State whether this messaeg is a discussion
     *
     * @return {boolean}
     */
    isDiscussion: function () {
        return this._isDiscussion;
    },
    /**
     * State whether this message is linked to a conversation (channel, DM, mailbox, livechat, etc.)
     * Useful to remove chatter messages not linked to a conversation.
     *
     * @return {boolean}
     */
    isLinkedToConversation: function () {
        return (this._conversationIDs && this._conversationIDs.length > 0);
    },
    /**
     * State whether this message is linked to a document
     *
     * Usually, if this is true, then this message comes from a document chat,
     * but the document model could be a channel. In that case, the document
     * resID tells the channel that this message originally comes from.
     *
     * @return {boolean}
     */
    isLinkedToDocument: function () {
        return !!(this._documentModel && this._documentResID);
    },
    /**
     * State whether this message is needaction
     *
     * @return {boolean}
     */
    isNeedaction: function () {
        return _.contains(this._conversationIDs, 'mailbox_inbox');
    },
    /**
     * State whether this message is a note (i.e. a message from "Log note")
     *
     * @return {boolean}
     */
    isNote: function () {
        return this._isNote;
    },
    /**
     * State whether this message is starred
     *
     * @return {boolean}
     */
    isStarred: function () {
        return _.contains(this._conversationIDs, 'mailbox_starred');
    },
    /**
     * State whether this message is a system notification
     *
     * @return {boolean}
     */
    isSystemNotification: function () {
        return (this._type === 'notification' && this._documentModel === 'mail.channel')
            || this._isTransient();
    },
    /**
     * Unregister mailbox with ID `mailboxID` from this message
     *
     * @param {string} mailboxID ID of mailbox
     */
    removeMailbox: function (mailboxID) {
        var conversationID = 'mailbox_' + mailboxID;
        this._conversationIDs = _.without(this._conversationIDs, conversationID);
    },
    /**
     * Set whether the message is needaction or not.
     * If it is needaction, the message is moved to the "Inbox" mailbox.
     * Note that this function only applies it locally, the server is not aware
     *
     * @param {boolean} needaction if set, the message is needaction
     */
    setNeedaction: function (needaction) {
        if (needaction) {
            this._addMailbox('inbox');
        } else {
            this.removeMailbox('inbox');
        }
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
            this._addMailbox('starred');
        } else {
            this.removeMailbox('starred');
        }
    },
    /**
     * State whether this message should display the author
     *
     * @return {boolean}
     */
    shouldDisplayAuthor: function () {
        return this._displayAuthor;
    },
    /**
     * State whether this message should display the subject
     *
     * @return {boolean}
     */
    shouldDisplaySubject: function () {
        return this.hasSubject() && this.getType() !== 'notification' && !this.hasOriginChannel();
    },
    /**
     * State whether this message should redirect to the author page
     * when clicking on the author of this message.
     *
     * Do not redirect on author clicked of self-posted or Odoobot messages
     * (note: Odoobot is the default author of transient messages)
     *
     * @return {boolean}
     */
    shouldRedirectToAuthorPage: function () {
        return !this.isAuthor() && !this._isOdoobotAuthor();
    },
    /**
     * Toggle the star status of the message
     *
     * It relies on the star status of the message from the date of the server.
     * The star status is updated from a 'toggle_star' notification on the
     * longpoll bus
     *
     * @see {mail.ChatNotificationManager} for the receipt of 'toggle_star'
     *   notification after this rpc.
     *
     * @return {$.Promise}
     */
    toggleStarStatus: function () {
        return this._rpc({
                model: 'mail.message',
                method: 'toggle_message_starred',
                args: [[this._id]],
            });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a mailbox to the message
     * Useful when you mark a message as 'to do'.
     * This message will be available in 'Starred' conversation.
     *
     * @private
     * @param  {string} mailboxID
     */
    _addMailbox: function (mailboxID) {
        var conversationID = 'mailbox_' + mailboxID;
        if (!this._conversationIDs) {
            this._conversationIDs = [];
        }
        this._conversationIDs.push(conversationID);
        this._conversationIDs = _.uniq(this._conversationIDs);
    },
    /**
     * State if the author of this message is Odoobot
     * This is the default author for transient messages.
     *
     * @private
     * @return {boolean}
     */
    _isOdoobotAuthor: function () {
        return this._serverAuthorID === ODOOBOT_ID;
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
     * Compute url of attachments of this message
     *
     * @private
     */
    _processAttachmentURL: function () {
        _.each(this.getAttachments(), function (attachment) {
            attachment.url = '/web/content/' + attachment.id + '?download=true';
        });
    },
    /**
     * Convert the server-format body of the message to the client-format.
     * Basically, it processes emojis and url.
     *
     * @private
     */
    _processBody: function (emojis) {
        var self = this;
        _.each(emojis, function (emoji) {
            var unicode = emoji.unicode_source;
            var regexp = new RegExp("(?:^|\\s|<[a-z]*>)(" + unicode + ")(?=\\s|$|</[a-z]*>)", 'g');
            self._body = self._body.replace(regexp, ' <span class="o_mail_emoji">' + unicode + '</span> ');
        });

        // add anchor tags to urls
        self._body = mailUtils.parse_and_transform(self._body, mailUtils.add_link);
    },
    /**
     * Set the appropriate mailboxes to this message based on server data
     *
     * @private
     */
    _processMailboxes: function () {
        if (_.contains(this._needactionPartnerIDs, session.partner_id)) {
            this.setNeedaction(true);
        }
        if (_.contains(this._starredPartnerIDs, session.partner_id)) {
            this.setStarred(true);
        }
    },
    /**
     * Process origin channel of this message, if any
     *
     * @private
     */
    _processOriginChannel: function () {
        if (this._documentModel === 'mail.channel') {
            var channelIDs = _.without(this._conversationIDs, 'mailbox_inbox', 'mailbox_starred');
            var originChannelID = channelIDs.length === 1 ? channelIDs[0] : undefined;
            var channel = originChannelID && this.call('chat_service', 'getChannel', originChannelID);
            if (channel) {
                this._originChannelID = originChannelID;
                this._originChannelName = channel.getName();
            }
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
                        trackingValue.old_value = moment.utc(trackingValue.old_value).local().format('LLL');
                    }
                    if (trackingValue.new_value) {
                        trackingValue.new_value = moment.utc(trackingValue.new_value).local().format('LLL');
                    }
                } else if (trackingValue.field_type === 'date') {
                    if (trackingValue.old_value) {
                        trackingValue.old_value = moment(trackingValue.old_value).local().format('LL');
                    }
                    if (trackingValue.new_value) {
                        trackingValue.new_value = moment(trackingValue.new_value).local().format('LL');
                    }
                }
            });
        }
    },

});

return Message;

});
