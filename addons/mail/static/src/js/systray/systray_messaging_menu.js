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
        'show.bs.dropdown': '_onShowDropdown'
    },
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.counter = 0;
        this.filter = false;
        this.previews = [];
    },
    /**
     * @override
     */
    willStart: function () {
        return $.when(this._super.apply(this, arguments), this.call('mail_service', 'isReady'));
    },
    /**
     * @override
     */
    start: function () {
        this._$counter = this.$('.o_notification_counter');
        this._$content = this.$('.o_systray_menu_content');
        var mailBus = this.call('mail_service', 'getMailBus');
        mailBus.on('update_needaction', this, this._render);
        mailBus.on('new_channel', this, this._render);
        mailBus.on('update_thread_unread_counter', this, this._render);
        return this._super.apply(this, arguments)
                .then(this._getCounterAndPreviews.bind(this))
                .then(this._render.bind(this));
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
     * Compute the counter to display on the messaging menu, using data from
     * the mail service.
     *
     * @private
     * @returns {integer} the computed counter to display
     */
    _computeCounter: function () {
        var channels = this.call('mail_service', 'getChannels');
        var channelUnreadCounters = _.map(channels, function (channel) {
            return channel.getUnreadCounter();
        });
        var unreadChannelCounter = _.reduce(channelUnreadCounters, function (c1, c2) {
            return c1 + c2;
        }, 0);
        var inboxCounter = this.call('mail_service', 'getMailbox', 'inbox').getMailboxCounter();
        var mailFailureCounter = this.call('mail_service', 'getMailFailures').length;
        return unreadChannelCounter + inboxCounter + mailFailureCounter;
    },
    /**
     * Get counter and previews from the mail service.
     *
     * @private
     * @returns {$.Deferred} resolved when it receives counter and previews
     */
    _getCounterAndPreviews: function () {
        this.counter = this._computeCounter();
        return this._getPreviews().then(this._updatePreviews.bind(this));
    },
    /**
     * @private
     * @returns {$.Promise<Object[]>} resolved with list of previews that are
     *   compatible with the 'mail.Preview' template.
     */
    _getPreviews: function () {
        return this.call('mail_service', 'getSystrayPreviews', this.filter);
    },
    /**
     * Open discuss with the provided channel
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
     * Called when clicking on a preview related to a mail failure
     *
     * @private
     * @param {string} documentModel
     * @param {integer|undefined} [documentID=undefined]
     */
    _openMailFailurePreview: function (documentModel, documentID) {
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
     * Compute counter and previews, and render them.
     *
     * @private
     */
    _render: function () {
        var self = this;
        this._getCounterAndPreviews().then(function () {
            self.$el.toggleClass('o_no_notification', !self.counter);
            self._$counter.html(QWeb.render('mail.systray.Counter', { widget: self }));
            self._$content.html(QWeb.render('mail.systray.MessagingMenu.Content', { widget: self }));
        });
    },
    /**
     * @private
     * @param {Object[]} list of objects that are compatible with mail.Preview
     *   template.
     */
    _updatePreviews: function (previews) {
        this.previews = previews;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Note: we stop propagation of the event, so that jQuery does not close
     * the dropdown menu.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFilterButton: function (ev) {
        ev.stopPropagation();
        this.filter = $(ev.currentTarget).data('filter');
        this._render();
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
        var documentID = $target.data('document-id');
        var documentModel = $target.data('document-model');

        if (previewID === 'mail_failure') {
            this._openMailFailurePreview(documentModel, documentID);
        } else if (previewID === 'mailbox_inbox') {
            // inbox preview for non-document thread,
            // e.g. needaction message of channel
            this._openDocument(documentModel, documentID);
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
        var thread;
        var $preview = $(ev.currentTarget).closest('.o_mail_preview');
        var previewID = $preview.data('preview-id');
        var documentModel = $preview.data('document-model');
        if (previewID === 'mailbox_inbox') {
            var documentID = $preview.data('document-id');
            var inbox = this.call('mail_service', 'getMailbox', 'inbox');
            var messages = inbox.getMessages({
                documentModel: documentModel,
                documentID: documentID,
            });
            var messageIDs = _.map(messages, function (message) {
                return message.getID();
            });
            this.call('mail_service', 'markMessagesAsRead', messageIDs);
        } else if (previewID === 'mail_failure') {
            var unreadCounter = $preview.data('unread-counter');
            this.do_action('mail.mail_resend_cancel_action', {
                additional_context: {
                    default_model: documentModel,
                    unread_counter: unreadCounter
                }
            });
        } else {
            // this is mark as read on a thread
            thread = this.call('mail_service', 'getThread', previewID);
            if (thread) {
                thread.markAsRead();
            }
        }
    },
    /**
     * Called when opening the systray messaging menu. It should always use
     * the 1st filter
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onShowDropdown: function (ev) {
        this.filter = undefined;
        this._render();
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
