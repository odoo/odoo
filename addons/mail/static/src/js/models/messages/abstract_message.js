odoo.define('mail.model.AbstractMessage', function (require) {
"use strict";

var mailUtils = require('mail.utils');

var Class = require('web.Class');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');

var _t = core._t;

/**
 * This is an abstract class for modeling messages in JS.
 * The purpose of this interface is to make im_livechat compatible with
 * mail.widget.Thread, as this widget was designed to work with messages that
 * are instances of mail.model.Messages.
 *
 * Ideally, im_livechat should also handle mail.model.Message, but this is not
 * feasible for the moment, as mail.model.Message requires mail.Manager to work,
 * and this module should not leak outside of the backend, hence the use of
 * mail.model.AbstractMessage as a work-around.
 */
var AbstractMessage =  Class.extend({

    /**
     * @param {Widget} parent
     * @param {Object} data
     * @param {Array} [data.attachment_ids=[]]
     * @param {Array} [data.author_id]
     * @param {string} [data.body = ""]
     * @param {string} [data.date] the server-format date time of the message.
     *   If not provided, use current date time for this message.
     * @param {integer} data.id
     * @param {boolean} [data.is_discussion = false]
     * @param {boolean} [data.is_notification = false]
     * @param {string} [data.message_type = undefined]
     */
    init: function (parent, data) {
        this._attachmentIDs = data.attachment_ids || [];
        this._body = data.body || "";
        // by default: current datetime
        this._date = data.date ? moment(time.str_to_datetime(data.date)) : moment();
        this._id = data.id;
        this._isDiscussion = data.is_discussion;
        this._isNotification = data.is_notification;
        this._serverAuthorID = data.author_id;
        this._type = data.message_type || undefined;

        this._processAttachmentURL();
        this._attachmentIDs.forEach(function (attachment) {
            attachment.filename = attachment.filename || attachment.name || _t("unnamed");
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
     * Threads do not have an im status by default
     *
     * @return {undefined}
     */
    getAuthorImStatus: function () {
        return undefined;
    },
    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @abstract
     * @return {string}
     */
    getAvatarSource: function () {},
    /**
     * Get the body content of this message
     *
     * @return {string}
     */
    getBody: function () {
        return this._body;
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
     * Get the name of the author, if there is an author of this message
     * If there are no author of this message, returns 'null'
     *
     * @return {string}
     */
    getDisplayedAuthor: function () {
        return this.hasAuthor() ? this._getAuthorName() : null;
    },
    /**
     * Get the server ID (number) of this message
     *
     * @override
     * @return {integer}
     */
    getID: function () {
        return this._id;
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
     * Get the time elapsed between sent message and now
     *
     * @return {string}
     */
    getTimeElapsed: function () {
        return mailUtils.timeFromNow(this.getDate());
    },
    /**
     * Get the type of message (e.g. 'comment', 'email', 'notification', ...)
     * By default, messages are of type 'undefined'
     *
     * @override
     * @return {string|undefined}
     */
    getType: function () {
        return this._type;
    },
    /**
     * State whether this message contains some attachments.
     *
     * @override
     * @return {boolean}
     */
    hasAttachments: function () {
        return this.getAttachments().length > 0;
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
     * By default, messages do not have any customer email data
     *
     * @return {boolean}
     */
    hasCustomerEmailData: function () {
        return false;
    },
    /**
     * State whether this message has an email of its sender.
     * By default, messages do not have any email of its sender.
     *
     * @return {string}
     */
    hasEmailFrom: function () {
        return false;
    },
    /**
     * State whether this image contains images attachments
     *
     * @return {boolean}
     */
    hasImageAttachments: function () {
        return _.some(this.getAttachments(), function (attachment) {
            return attachment.mimetype && attachment.mimetype.split('/')[0] === 'image';
        });
    },
    /**
     * State whether this image contains non-images attachments
     *
     * @return {boolean}
     */
    hasNonImageAttachments: function () {
        return _.some(this.getAttachments(), function (attachment) {
            return !(attachment.mimetype && attachment.mimetype.split('/')[0] === 'image');
        });
    },
    /**
     * State whether this message originates from a channel.
     * By default, messages do not originate from a channel.
     *
     * @override
     * @return {boolean}
     */
    originatesFromChannel: function () {
        return false;
    },
    /**
     * State whether this message has a subject
     * By default, messages do not have any subject.
     *
     * @return {boolean}
     */
    hasSubject: function () {
        return false;
    },
    /**
     * State whether this message is empty
     *
     * @return {boolean}
     */
    isEmpty: function () {
        return !this.hasTrackingValues() &&
        !this.hasAttachments() &&
        !this.getBody();
    },
    /**
     * By default, messages do not have any subtype description
     *
     * @return {boolean}
     */
    hasSubtypeDescription: function () {
        return false;
    },
    /**
     * State whether this message contains some tracking values
     * By default, messages do not have any tracking values.
     *
     * @return {boolean}
     */
    hasTrackingValues: function () {
        return false;
    },
    /**
     * State whether this message is a discussion
     *
     * @return {boolean}
     */
    isDiscussion: function () {
        return this._isDiscussion;
    },
    /**
     * State whether this message is linked to a document thread
     * By default, messages are not linked to a document thread.
     *
     * @return {boolean}
     */
    isLinkedToDocumentThread: function () {
        return false;
    },
    /**
     * State whether this message is needaction
     * By default, messages are not needaction.
     *
     * @return {boolean}
     */
    isNeedaction: function () {
        return false;
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
     * State whether this message is a notification
     *
     * User notifications are defined as either
     *      - notes
     *      - pushed to user Inbox or email through classic notification process
     *      - not linked to any document, meaning model and res_id are void
     *
     * This is useful in order to display white background for user
     * notifications in chatter
     *
     * @returns {boolean}
     */
    isNotification: function () {
        return this._isNotification;
    },
    /**
     * State whether this message is starred
     * By default, messages are not starred.
     *
     * @return {boolean}
     */
    isStarred: function () {
        return false;
    },
    /**
     * State whether this message is a system notification
     * By default, messages are not system notifications
     *
     * @override
     * @return {boolean}
     */
    isSystemNotification: function () {
        return false;
    },
    /**
     * States whether the current message needs moderation in general.
     * By default, messages do not require any moderation.
     *
     * @returns {boolean}
     */
    needsModeration: function () {
        return false;
    },
    /**
     * @params {integer[]} attachmentIDs
     */
    removeAttachments: function (attachmentIDs) {
        this._attachmentIDs = _.reject(this._attachmentIDs, function (attachment) {
            return _.contains(attachmentIDs, attachment.id);
        });
    },
    /**
     * State whether this message should redirect to the author
     * when clicking on the author of this message.
     *
     * Do not redirect on author clicked of self-posted messages.
     *
     * @return {boolean}
     */
    shouldRedirectToAuthor: function () {
        return !this._isMyselfAuthor();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the name of the author of this message.
     * If there are no author of this messages, returns '' (empty string).
     *
     * @private
     * @returns {string}
     */
    _getAuthorName: function () {
        if (!this.hasAuthor()) {
            return "";
        }
        return this._serverAuthorID[1];
    },
    /**
     * State whether the current user is the author of this message
     *
     * @private
     * @return {boolean}
     */
    _isMyselfAuthor: function () {
        return this.hasAuthor() && (this.getAuthorID() === session.partner_id);
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

});

return AbstractMessage;

});
