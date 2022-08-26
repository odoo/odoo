/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import Class from 'web.Class';
import { _t } from 'web.core';
import session from 'web.session';
import time from 'web.time';

/**
 * This is a message that is handled by im_livechat, without making use of the
 * mail.Manager. The purpose of this is to make im_livechat compatible with
 * mail.widget.Thread.
 *
 * @see @im_livechat/legacy/models/public_livechat_message for more information.
 */
const PublicLivechatMessage = Class.extend({

    /**
     * @param {@im_livechat/legacy/widgets/livechat_button} parent
     * @param {Messaging} messaging
     * @param {Object} data
     * @param {Array} [data.author_id]
     * @param {string} [data.body = ""]
     * @param {string} [data.date] the server-format date time of the message.
     *   If not provided, use current date time for this message.
     * @param {integer} data.id
     * @param {boolean} [data.is_discussion = false]
     * @param {boolean} [data.is_notification = false]
     * @param {string} [data.message_type = undefined]
     */
    init(parent, messaging, data) {
        this.messaging = messaging;
        this._body = data.body || "";
        // by default: current datetime
        this._date = data.date ? moment(time.str_to_datetime(data.date)) : moment();
        this._id = data.id;
        this._isDiscussion = data.is_discussion;
        this._isNotification = data.is_notification;
        this._serverAuthorID = data.author_id;
        this._type = data.message_type || undefined;

        this._defaultUsername = this.messaging.publicLivechatGlobal.options.default_username;
        this._serverURL = this.messaging.publicLivechatGlobal.serverUrl;

        if (parent.messaging.publicLivechatGlobal.livechatButtonView.isChatbot) {
            this._chatbotStepId = data.chatbot_script_step_id;
            this._chatbotStepAnswers = data.chatbot_step_answers;
            this._chatbotStepAnswerId = data.chatbot_selected_answer_id;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the server ID (number) of the author of this message
     * If there are no author, return -1;
     *
     * @return {integer}
     */
    getAuthorID() {
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
    getAuthorImStatus() {
        return undefined;
    },
    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @return {string}
     */
    getAvatarSource() {
        let source = this._serverURL;
        if (this.hasAuthor()) {
            source += `/im_livechat/operator/${this.getAuthorID()}/avatar`;
        } else {
            source += '/mail/static/src/img/smiley/avatar.jpg';
        }
        return source;
    },
    /**
     * Get the body content of this message
     *
     * @return {string}
     */
    getBody() {
        return this._body;
    },
    /**
     * @return {string}
     */
    getChatbotStepId() {
        return this._chatbotStepId;
    },
    /**
     * @return {string}
     */
    getChatbotStepAnswers() {
        return this._chatbotStepAnswers;
    },
    /**
     * @return {string}
     */
    getChatbotStepAnswerId() {
        return this._chatbotStepAnswerId;
    },
    /**
     * @return {moment}
     */
    getDate() {
        return this._date;
    },
    /**
     * Get the date day of this message
     *
     * @return {string}
     */
    getDateDay() {
        const date = this.getDate().format('YYYY-MM-DD');
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
     * Rule of precedence for the displayed author::
     *
     *      author name > default usernane
     *
     * @return {string}
     */
    getDisplayedAuthor() {
        return (this.hasAuthor() ? this._getAuthorName() : null) || this._defaultUsername;
    },
    /**
     * Get the server ID (number) of this message
     *
     * @return {integer}
     */
    getID() {
        return this._id;
    },
    /**
     * Gets the class to use as the notification icon.
     *
     * @returns {string}
     */
    getNotificationIcon() {
        if (!this.hasNotificationsError()) {
            return 'fa fa-envelope-o';
        }
        return 'fa fa-envelope';
    },
    /**
     * Gets the list of notifications of this message, in no specific order.
     * By default messages do not have notifications.
     *
     * @returns {Object[]}
     */
    getNotifications() {
        return [];
    },
    /**
     * Gets the text to display next to the notification icon.
     *
     * @returns {string}
     */
    getNotificationText() {
        return '';
    },
    /**
     * Get the time elapsed between sent message and now
     *
     * @return {string}
     */
    getTimeElapsed() {
        return mailUtils.timeFromNow(this.getDate());
    },
    /**
     * Get the type of message (e.g. 'comment', 'email', 'notification', ...)
     * By default, messages are of type 'undefined'
     *
     * @return {string|undefined}
     */
    getType() {
        return this._type;
    },
    /**
     * State whether this message has an author
     *
     * @return {boolean}
     */
    hasAuthor() {
        return !!(this._serverAuthorID && this._serverAuthorID[0]);
    },
    /**
     * State whether this message has an email of its sender.
     * By default, messages do not have any email of its sender.
     *
     * @return {string}
     */
    hasEmailFrom() {
        return false;
    },
    /**
     * States whether this message has some notifications.
     *
     * @returns {boolean}
     */
    hasNotifications() {
        return this.getNotifications().length > 0;
    },
    /**
     * States whether this message has notifications that are in error.
     *
     * @returns {boolean}
     */
    hasNotificationsError() {
        return this.getNotifications().some(notif =>
            notif.notification_status === 'exception' ||
            notif.notification_status === 'bounce'
        );
    },
    /**
     * State whether this message has a subject
     * By default, messages do not have any subject.
     *
     * @return {boolean}
     */
    hasSubject() {
        return false;
    },
    /**
     * State whether this message is empty
     *
     * @return {boolean}
     */
    isEmpty() {
        return !this.hasTrackingValues() &&
        !this.getBody();
    },
    /**
     * By default, messages do not have any subtype description
     *
     * @return {boolean}
     */
    hasSubtypeDescription() {
        return false;
    },
    /**
     * State whether this message contains some tracking values
     * By default, messages do not have any tracking values.
     *
     * @return {boolean}
     */
    hasTrackingValues() {
        return false;
    },
    /**
     * State whether this message is a discussion
     *
     * @return {boolean}
     */
    isDiscussion() {
        return this._isDiscussion;
    },
    /**
     * State whether this message is linked to a document thread
     * By default, messages are not linked to a document thread.
     *
     * @return {boolean}
     */
    isLinkedToDocumentThread() {
        return false;
    },
    /**
     * State whether this message is needaction
     * By default, messages are not needaction.
     *
     * @return {boolean}
     */
    isNeedaction() {
        return false;
    },
    /**
     * State whether this message is a note (i.e. a message from "Log note")
     *
     * @return {boolean}
     */
    isNote() {
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
    isNotification() {
        return this._isNotification;
    },
    /**
     * State whether this message is starred
     * By default, messages are not starred.
     *
     * @return {boolean}
     */
    isStarred() {
        return false;
    },
    /**
     * State whether this message is a system notification
     * By default, messages are not system notifications
     *
     * @return {boolean}
     */
    isSystemNotification() {
        return false;
    },
    /**
     * States whether the current message needs moderation in general.
     * By default, messages do not require any moderation.
     *
     * @returns {boolean}
     */
    needsModeration() {
        return false;
    },
    setChatbotStepAnswerId(chatbotStepAnswerId) {
        this._chatbotStepAnswerId = chatbotStepAnswerId;
    },
    /**
     * State whether this message should redirect to the author
     * when clicking on the author of this message.
     *
     * Do not redirect on author clicked of self-posted messages.
     *
     * @return {boolean}
     */
    shouldRedirectToAuthor() {
        return !this._isMyselfAuthor();
    },

    isVisitorTheAuthor() {
        return !this.hasAuthor() || this._isMyselfAuthor();
    },

    isOperatorTheAuthor() {
        return this.hasAuthor() && !this._isMyselfAuthor();
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
    _getAuthorName() {
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
    _isMyselfAuthor() {
        return this.hasAuthor() && (this.getAuthorID() === session.partner_id);
    },

});

export default PublicLivechatMessage;
