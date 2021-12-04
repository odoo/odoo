odoo.define('mail.systray.MessagingMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var QWeb = core.qweb;

/**
 * Menu item appended in the systray part of the navbar
 *
 * The menu item indicates the counter of needactions + unread messages in chat
 * channels. When clicking on it, it toggles a dropdown containing a preview of
 * each pinned channels (except mailbox and mass mailing channels) with a quick
 * link to open them in chat windows. It also contains a direct link to the
 * Inbox in Discuss.
 **/
var MessagingMenu = Widget.extend({
    name: 'messaging_menu',
    template:'mail.systray.MessagingMenu',
    events: {
        'click .o_mail_preview': '_onClickPreview',
        'click .o_filter_button': '_onClickFilterButton',
        'click .o_new_message': '_onClickNewMessage',
        'click .o_mail_preview_mark_as_read': '_onClickPreviewMarkAsRead',
        'click .o_thread_window_expand': '_onClickExpand',
        'show.bs.dropdown': '_onShowDropdown',
        'hide.bs.dropdown': '_onHideDropdown',
    },
    /**
     * @override
     */
    start: function () {
        this._$filterButtons = this.$('.o_filter_button');
        this._$previews = this.$('.o_mail_systray_dropdown_items');
        this._filter = false;
        this._isMessagingReady = this.call('mail_service', 'isReady');
        this._updateCounter();
        var mailBus = this.call('mail_service', 'getMailBus');
        mailBus.on('messaging_ready', this, this._onMessagingReady);
        mailBus.on('update_needaction', this, this._updateCounter);
        mailBus.on('new_channel', this, this._updateCounter);
        mailBus.on('update_thread_unread_counter', this, this._updateCounter);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * States whether the widget is in mobile mode or not.
     * This is used by the template.
     *
     * @returns {boolean}
     */
    isMobile: function () {
        return config.device.isMobile;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on a preview related to a mail failure
     *
     * @private
     * @param {$.Element} $target DOM of preview element clicked
     */
    _clickMailFailurePreview: function ($target) {
        var documentID = $target.data('document-id');
        var documentModel = $target.data('document-model');
        if (documentModel && documentID) {
            this._openDocument(documentModel, documentID);
        } else if (documentModel !== 'mail.channel') {
            // preview of mail failures grouped to different document of same model
            this.do_action({
                name: "Mail failures",
                type: 'ir.actions.act_window',
                view_mode: 'kanban,list,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                target: 'current',
                res_model: documentModel,
                domain: [['message_has_error', '=', true]],
            });
        }
    },
    /**
     * Compute the counter next to the systray messaging menu. This counter is
     * the sum of unread messages in channels, the counter of the mailbox inbox,
     * and the amount of mail failures.
     *
     * @private
     * @returns {integer}
     */
    _computeCounter: function () {
        var channels = this.call('mail_service', 'getChannels');
        var channelUnreadCounters = _.map(channels, function (channel) {
            return channel.getUnreadCounter();
        });
        var unreadChannelCounter = _.reduce(channelUnreadCounters, function (acc, c) {
            return c > 0 ? acc + 1 : acc;
        }, 0);
        var inboxCounter = this.call('mail_service', 'getMailbox', 'inbox').getMailboxCounter();
        var mailFailureCounter = this.call('mail_service', 'getMailFailures').length;

        return unreadChannelCounter + inboxCounter + mailFailureCounter;
    },
    /**
     * @private
     * @returns {Promise<Object[]>} resolved with list of previews that are
     *   compatible with the 'mail.Preview' template.
     */
    _getPreviews: function () {
        return this.call('mail_service', 'getSystrayPreviews', this._filter);
    },
    /**
     * @private
     * @return {boolean} whether the messaging menu is shown or not.
     */
    _isShown: function () {
        return this.$el.hasClass('show');
    },
    /**
     * Process Preview Mark As Read
     *
     * @private
     * @param {Element} $preview
     */
    _markAsRead: function ($preview) {
        var previewID = $preview.data('preview-id');
        if (previewID === 'mailbox_inbox') {
            var messageIDs = $preview.data('message-ids');

            if (typeof messageIDs === 'string') {
                messageIDs = messageIDs.split(',').map(id => Number(id));
            } else {
                messageIDs = [$preview.data('message-ids')];
            }

            this.call('mail_service', 'markMessagesAsRead', messageIDs);
        } else if (previewID === 'mail_failure') {
            var documentModel = $preview.data('document-model');
            var unreadCounter = $preview.data('unread-counter');
            this.do_action('mail.mail_resend_cancel_action', {
                additional_context: {
                    default_model: documentModel,
                    unread_counter: unreadCounter
                }
            });
        } else {
            // this is mark as read on a thread
            var thread = this.call('mail_service', 'getThread', previewID);
            if (thread) {
                thread.markAsRead();
            }
        }
    },
    /**
     * Open discuss
     *
     * @private
     * @param {integer} [channelID] if set, auto-select this channel when
     *   opening the discuss app.
     */
    _openDiscuss: function (channelID) {
        var self = this;
        var discussOptions = { clear_breadcrumbs: true };

        if (channelID) {
            discussOptions.active_id = channelID;
        }

        this.do_action('mail.action_discuss', discussOptions)
            .then(function () {
                // we cannot 'go back to previous page' otherwise
                self.trigger_up('hide_home_menu');
                core.bus.trigger('change_menu_section',
                    self.call('mail_service', 'getDiscussMenuID'));
            });
    },
    /**
     * Open the document
     *
     * @private
     * @param {string} documentModel the model of the document
     * @param {integer} documentID
     */
    _openDocument: function (documentModel, documentID) {
        if (documentModel === 'mail.channel') {
            this._openDiscuss(documentID);
        } else {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: documentModel,
                views: [[false, 'form']],
                res_id: documentID
            });
        }
    },
    /**
     * Render the list of conversation previews
     *
     * @private
     * @param {Object} previews list of valid objects for preview rendering
     *   (see mail.Preview template)
     */
    _renderPreviews: function (previews) {
        this._$previews.html(QWeb.render('mail.systray.MessagingMenu.Previews', {
            previews: previews,
        }));
    },
    /**
     * Get and render list of previews, based on the selected filter
     *
     * preview shows the last message of a channel with inline format.
     * There is a hack where filter "All" also shows preview of chatter
     * messages (which are not channels).
     *
     * List of filters:
     *
     *  1. All
     *      - filter:   undefined
     *      - previews: last messages of all non-mailbox channels, in addition
     *                  to last messages of chatter (get from inbox)
     *
     *  2. Channel
     *      - filter:   "Channels"
     *      - previews: last messages of all non-mailbox and non-DM channels
     *
     *  3. Chat
     *      - filter:   "Chat"
     *      - previews: last messages of all DM channels
     *
     * @private
     */
    _updatePreviews: function () {
        // Display spinner while waiting for conversations preview
        this._$previews.html(QWeb.render('Spinner'));
        if (!this._isMessagingReady) {
            return;
        }
        this._getPreviews()
            .then(this._renderPreviews.bind(this));
    },
    /**
     * Update the counter on the systray messaging menu icon.
     * The counter display the number of unread messages in channels (DM included), the number of
     * messages in Inbox mailbox, and the number of mail failures.
     * Also updates the previews if the messaging menu is open.
     *
     * Note that the number of unread messages in document thread are ignored, because they are
     * already considered in the number of messages in Inbox with the current design.
     * Also, some unread messages in channel can also be in inbox, so they are considered twice in
     * the counter. This is intended, as the number of needaction messages in a channel are
     * separately considered in the messaging menu from the unread messages, even though a message
     * can be both unread and needaction (such a message increments the counter twice).
     *
     * The global counter of the messaging menu should match the counter next to each of the preview
     * item when the messaging menu is open.
     *
     * @private
     */
    _updateCounter: function () {
        if (!this._isMessagingReady) {
            return;
        }
        var counter = this._computeCounter();
        this.$('.o_mail_messaging_menu_icon').removeClass('fa-spinner fa-spin');
        this.$('.o_notification_counter').text(counter);
        this.$el.toggleClass('o_no_notification', !counter);
        if (this._isShown()) {
            this._updatePreviews();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onShowDropdown: function () {
        document.body.classList.add('modal-open');
        this._updatePreviews();
    },
    /**
     * @private
     */
    _onHideDropdown: function () {
        document.body.classList.remove('modal-open');
    },
    /**
     * Opens the related document
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickExpand: function (ev) {
        ev.stopPropagation();
        var $preview = $(ev.currentTarget).closest('.o_mail_preview');
        var documentModel = $preview.data('document-model');
        var documentID = $preview.data('document-id');
        this._openDocument(documentModel, documentID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFilterButton: function (ev) {
        ev.stopPropagation();
        this._$filterButtons.removeClass('active');
        var $target = $(ev.currentTarget);
        $target.addClass('active');
        this._filter = $target.data('filter');
        this._updatePreviews();
    },
    /**
     * @private
     */
    _onClickNewMessage: function () {
        this.call('mail_service', 'openBlankThreadWindow');
    },
    /**
     * When a preview is clicked on, we want to open the related object
     * (thread, mail failure, etc.)
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPreview: function (ev) {
        var $target = $(ev.currentTarget);
        var previewID = $target.data('preview-id');

        if (previewID === 'mail_failure') {
            this._clickMailFailurePreview($target);
        } else if (previewID === 'mailbox_inbox') {
            // inbox preview for non-document thread,
            // e.g. needaction message of channel
            var documentID = $target.data('document-id');
            var documentModel = $target.data('document-model');
            if (!documentModel) {
                this._openDiscuss('mailbox_inbox');
            } else {
                this._openDocument(documentModel, documentID);
            }
        } else {
            // preview of thread
            this.call('mail_service', 'openThread', previewID);
        }
    },
    /**
     * When a preview "Mark as read" button is clicked on, we want mark message
     * as read
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPreviewMarkAsRead: function (ev) {
        ev.stopPropagation();
        var $preview = $(ev.currentTarget).closest('.o_mail_preview');
        this._markAsRead($preview);
    },
    /**
     * @private
     */
    _onMessagingReady: function () {
        if (this._isMessagingReady) {
            return;
        }
        this._isMessagingReady = true;
        this._updateCounter();
    },
});

// Systray menu items display order matches order in the list
// lower index comes first, and display is from right to left.
// For messagin menu, it should come before activity menu, if any
// otherwise, it is the next systray item.
var activityMenuIndex = _.findIndex(SystrayMenu.Items, function (SystrayMenuItem) {
    return SystrayMenuItem.prototype.name === 'activity_menu';
});
if (activityMenuIndex > 0) {
    SystrayMenu.Items.splice(activityMenuIndex, 0, MessagingMenu);
} else {
    SystrayMenu.Items.push(MessagingMenu);
}

return MessagingMenu;

});
