odoo.define('mail.systray', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var QWeb = core.qweb;

/**
 * Menu item appended in the systray part of the navbar
 *
 * The menu item indicates the counter of needactions + unread messages in chat channels. When
 * clicking on it, it toggles a dropdown containing a preview of each pinned channels (except
 * mailbox and mass mailing channels) with a quick link to open them in chat windows. It also
 * contains a direct link to the Inbox in Discuss.
 **/
var MessagingMenu = Widget.extend({
    template:'mail.systray.MessagingMenu',
    events: {
        'click': '_onClick',
        'click .o_mail_conversation_preview': '_onClickConversationPreview',
        'click .o_filter_button': '_onClickFilterButton',
        'click .o_new_message': '_onClickNewMessage',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile; // used by the template
    },
    willStart: function () {
        return $.when(this.call('chat_service', 'isReady'));
    },
    start: function () {
        this._$filterButtons = this.$('.o_filter_button');
        this._$conversationPreviews = this.$('.o_mail_navbar_dropdown_channels');
        this._filter = false;
        var chatBus = this.call('chat_service', 'getChatBus');
        chatBus.on('update_needaction', this, this._updateCounter);
        chatBus.on('update_conversation_unread_counter', this, this._updateCounter);
        this._updateCounter();
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {boolean} whether the messaging menu is open or not.
     */
    _isOpen: function () {
        return this.$el.hasClass('open');
    },
    /**
     * Render the list of conversation previews
     *
     * @private
     * @param {<mail.model.ConversationPreview[]>} previews (from channels and messages)
     */
    _renderConversationPreviews: function (previews) {
        this._$conversationPreviews.html(QWeb.render('mail.conversation.Previews', {
            conversationPreviews: previews,
        }));
    },
    /**
     * Get and render list of conversations preview, based on the selected filter
     *
     * Conversation preview shows the last message of a channel with inline format.
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
    _updateConversationsPreview: function () {
        var self = this;

        // Display spinner while waiting for conversations preview
        this._$conversationPreviews.html(QWeb.render('Spinner'));
        this.call('chat_service', 'isReady').then(function () {
            // Select channels based on filter
            var allConversations = self.call('chat_service', 'getConversations');
            var channels = _.filter(allConversations, function (conversation) {
                if (self._filter === 'chat') {
                    return conversation.isChat();
                } else if (self._filter === 'channels') {
                    return !conversation.isChat() && conversation.getType() !== 'mailbox';
                } else {
                    return conversation.getType() !== 'mailbox';
                }
            });
            var channelPreviewsDef = self.call('chat_service', 'getChannelPreviews', channels);

            // 'All' filter, show messages preview from inbox
            var inboxPreviewsDef;
            if (self._filter === 'mailbox_inbox' || !self._filter) {
                var inbox = self.call('chat_service', 'getMailbox', 'inbox');
                inboxPreviewsDef = inbox.getMessagePreviews();
            } else {
                inboxPreviewsDef = $.when([]);
            }

            $.when(channelPreviewsDef, inboxPreviewsDef)
                .then(function (channelPreviews, messagePreviews) {
                    // message previews before channel previews
                    var allPreviews = _.union(messagePreviews, channelPreviews);
                    self._renderConversationPreviews(allPreviews);
                });
        });
    },
    /**
     * Update the counter on the messaging menu icon
     *
     * The counter is updated from data in chat_service.
     * Also updates channels preview if the messaging menu is open.
     *
     * @private
     */
    _updateCounter: function () {
        var inbox = this.call('chat_service', 'getMailbox', 'inbox');
        var starred = this.call('chat_service', 'getMailbox', 'starred');
        var needactionCounter = inbox.getMailboxCounter();
        var unreadConversationCounter = starred.getMailboxCounter();
        var counter =  needactionCounter + unreadConversationCounter;
        this.$('.o_notification_counter').text(counter);
        this.$el.toggleClass('o_no_notification', !counter);
        if (this._isOpen()) {
            this._updateConversationsPreview();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function () {
        if (!this._isOpen()) {
            this._updateConversationsPreview();  // we are opening the dropdown so update its content
        }
    },
    /**
     * When a conversation preview is clicked on, we want to open chat/channel window
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickConversationPreview: function (ev) {
        var self = this;
        var conversationID = $(ev.currentTarget).data('conversation_id');
        if (conversationID === 'mailbox_inbox') {
            var resID = $(ev.currentTarget).data('res_id');
            var resModel = $(ev.currentTarget).data('res_model');
            if (resModel && resID) {
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: resModel,
                    views: [[false, 'form']],
                    res_id: resID
                });
            } else {
                this.do_action('mail.mail_channel_action_client_chat', {clear_breadcrumbs: true})
                    .then(function () {
                        self.trigger_up('hide_home_menu'); // we cannot 'go back to previous page' otherwise
                        core.bus.trigger('change_menu_section', self.call('chat_service', 'getDiscussMenuID'));
                    });
            }
        } else {
            var conversation = this.call('chat_service', 'getConversation', conversationID);
            if (conversation) {
                conversation.open();
            }
        }
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
        this._updateConversationsPreview();
    },
    /**
     * @private
     */
    _onClickNewMessage: function () {
        this.call('chat_service', 'openChatWithoutSession');
    },
});

/**
 * Menu item appended in the systray part of the navbar, redirects to the next activities of all app
 */
var ActivityMenu = Widget.extend({
    template:'mail.systray.ActivityMenu',
    events: {
        'click': '_onActivityMenuClick',
        'click .o_mail_conversation_preview': '_onActivityFilterClick',
    },
    willStart: function () {
        return $.when(this.call('chat_service', 'isReady'));
    },
    start: function () {
        this.$activities_preview = this.$('.o_mail_navbar_dropdown_channels');
        this.call('chat_service', 'getChatBus').on('activity_updated', this, this._updateCounter);
        this._updateCounter();
        this._updateActivityPreview();
        return this._super();
    },
    //--------------------------------------------------
    // Private
    //--------------------------------------------------
    /**
     * Make RPC and get current user's activity details
     * @private
     */
    _getActivityData: function () {
        var self = this;

        return self._rpc({
            model: 'res.users',
            method: 'activity_user_count',
            kwargs: {
                context: session.user_context,
            },
        }).then(function (data) {
            self._activities = data;
            self.activityCounter = _.reduce(data, function (total_count, p_data) { return total_count + p_data.total_count; }, 0);
            self.$('.o_notification_counter').text(self.activityCounter);
            self.$el.toggleClass('o_no_notification', !self.activityCounter);
        });
    },
    /**
     * Get particular model view to redirect on click of activity scheduled on that model.
     * @private
     * @param {string} model
     */
    _getActivityModelViewID: function (model) {
        return this._rpc({
            model: model,
            method: 'get_activity_view_id'
        });
    },
    /**
     * Check wether activity systray dropdown is open or not
     * @private
     * @returns {boolean}
     */
    _isOpen: function () {
        return this.$el.hasClass('open');
    },
    /**
     * Update(render) activity system tray view on activity updation.
     * @private
     */
    _updateActivityPreview: function () {
        var self = this;
        self._getActivityData().then(function (){
            self.$activities_preview.html(QWeb.render('mail.systray.ActivityMenuPreview', {
                activities : self._activities
            }));
        });
    },
    /**
     * update counter based on activity status(created or Done)
     * @private
     * @param {Object} [data] key, value to decide activity created or deleted
     * @param {String} [data.type] notification type
     * @param {Boolean} [data.activity_deleted] when activity deleted
     * @param {Boolean} [data.activity_created] when activity created
     */
    _updateCounter: function (data) {
        if (data) {
            if (data.activity_created) {
                this.activityCounter ++;
            }
            if (data.activity_deleted && this.activityCounter > 0) {
                this.activityCounter --;
            }
            this.$('.o_notification_counter').text(this.activityCounter);
            this.$el.toggleClass('o_no_notification', !this.activityCounter);
        }
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /**
     * Redirect to particular model view
     * @private
     * @param {MouseEvent} event
     */
    _onActivityFilterClick: function (event) {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_conversation_preview).
        var data = _.extend({}, $(event.currentTarget).data(), $(event.target).data());
        var context = {};
        if (data.filter === 'my') {
            context['search_default_activities_overdue'] = 1;
            context['search_default_activities_today'] = 1;
        } else {
            context['search_default_activities_' + data.filter] = 1;
        }
        this.do_action({
            type: 'ir.actions.act_window',
            name: data.model_name,
            res_model:  data.res_model,
            views: [[false, 'kanban'], [false, 'form']],
            search_view_id: [false],
            domain: [['activity_user_id', '=', session.uid]],
            context:context,
        });
    },
    /**
     * When menu clicked update activity preview if counter updated
     * @private
     * @param {MouseEvent} event
     */
    _onActivityMenuClick: function () {
        if (!this._isOpen()) {
            this._updateActivityPreview();
        }
    },
});

SystrayMenu.Items.push(MessagingMenu);
SystrayMenu.Items.push(ActivityMenu);

// to test activity and messaging menus in qunit test cases we need it
return {
    ActivityMenu: ActivityMenu,
    MessagingMenu: MessagingMenu,
};
});
