odoo.define('mail.chat_client_action_mobile', function (require) {
"use strict";

var ChatAction = require('mail.chat_client_action');
var chat_manager = require('mail.chat_manager');

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');

var QWeb = core.qweb;

if (!config.device.isMobile) {
    return;
}

ChatAction.include({
    template: 'mail.client_action_mobile',
    need_control_panel: false, // in mobile, we use a custom control panel
    events: _.extend(ChatAction.prototype.events, {
        'click .o_mail_mobile_tab': '_onMobileTabClicked',
        'click .o_channel_inbox_item': '_onMobileInboxButtonClicked',
        'click .o_mail_channel_preview': '_onMobileChannelClicked',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.currentState = this.defaultChannelID;
    },
    /**
     * @override
     */
    start: function () {
        this.$mainContent = this.$('.o_mail_chat_content');
        return this._super.apply(this, arguments)
            .then(this._updateControlPanel.bind(this));
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        if (this.channel && this._isInInboxTab()) {
            this.thread.scroll_to({offset: this.channels_scrolltop[this.channel.id]});
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        if (this._isInInboxTab()) {
            this.channels_scrolltop[this.channel.id] = this.thread.get_scrolltop();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Boolean} true iff we currently are in the Inbox tab
     */
    _isInInboxTab: function () {
        return _.contains(['channel_inbox', 'channel_starred'], this.currentState);
    },
    /**
     * @override
     * @private
     */
    _renderButtons: function () {
        var self = this;
        this._super.apply(this, arguments);
        _.each(['dm', 'public', 'private'], function (type) {
            var selector = '.o_mail_chat_button_' + type;
            self.$buttons.on('click', selector, self._onAddChannel.bind(self));
        });
    },
    /**
     * Overrides to only store the channel state if we are in the Inbox tab, as
     * this is the only tab in which we actually have a displayed channel
     *
     * @override
     * @private
     */
    _restoreChannelState: function () {
        if (this._isInInboxTab()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to toggle the visibility of the tabs when a message is selected
     *
     * @override
     * @private
     */
    _selectMessage: function () {
        this._super.apply(this, arguments);
        this.$('.o_mail_mobile_tabs').addClass('o_hidden');
    },
    /**
     * @override
     * @private
     */
    _setChannel: function (channel) {
        if (channel.type !== 'static') {
            chat_manager.detach_channel(channel);
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to only store the channel state if we are in the Inbox tab, as
     * this is the only tab in which we actually have a displayed channel
     *
     * @override
     * @private
     */
    _storeChannelState: function () {
        if (this.channel && this._isInInboxTab()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @private
     */
    _toggleSearchView: function () {
        this.searchviewDisplayed = !this.searchviewDisplayed;
        this.searchview.$el.toggleClass('o_hidden', !this.searchviewDisplayed);
        this.$buttons.toggleClass('o_hidden', this.searchviewDisplayed);
    },
    /**
     * Overrides to toggle the visibility of the tabs when a message is unselected
     *
     * @override
     * @private
     */
    _unselectMessage: function () {
        this._super.apply(this, arguments);
        this.$('.o_mail_mobile_tabs').removeClass('o_hidden');
    },
    /**
     * @override
     * @private
     */
    _updateChannels: function () {
        return this._updateContent(this.currentState);
    },
    /**
     * Redraws the content of the client action according to its current state.
     *
     * @private
     * @param {string} type the channel's type to display (e.g. 'channel_inbox',
     *   'channel_starred', 'dm'...).
     */
    _updateContent: function (type) {
        var self = this;
        var inInbox = type === 'channel_inbox' || type === 'channel_starred';
        if (!inInbox && this._isInInboxTab()) {
            // we're leaving the inbox, so store the thread scrolltop
            this._storeChannelState();
        }
        var previouslyInInbox = this._isInInboxTab();
        this.currentState = type;

        // fetch content to display
        var def;
        if (inInbox) {
            def = this._fetchAndRenderThread();
        } else {
            var channels = _.where(chat_manager.get_channels(), {type: type});
            def = chat_manager.get_channels_preview(channels);
        }
        return $.when(def).then(function (channelsPreview) {
            // update content
            if (inInbox) {
                if (!previouslyInInbox) {
                    self.$('.o_mail_chat_tab_pane').remove();
                    self.$mainContent.append(self.thread.$el);
                    self.$mainContent.append(self.extended_composer.$el);
                }
                self._restoreChannelState();
            } else {
                self.thread.$el.detach();
                self.extended_composer.$el.detach();
                var $content = $(QWeb.render("mail.chat.MobileTabPane", {
                    channels: channelsPreview,
                    get_message_body_preview: chat_manager.get_message_body_preview,
                    moment: moment,
                    partner_id: session.partner_id,
                    type: type,
                    widget: self,
                }));
                self._prepareAddChannelInput($content.find('.o_mail_add_channel input'), type);
                self.$mainContent.html($content);
            }

            // update control panel
            self.$buttons.find('button').addClass('o_hidden');
            self.$buttons.find('.o_mail_chat_button_' + type).removeClass('o_hidden');
            self.$buttons.find('.o_mail_chat_button_mark_read').toggleClass('o_hidden', type !== 'channel_inbox');
            self.$buttons.find('.o_mail_chat_button_unstar_all').toggleClass('o_hidden', type !== 'channel_starred');
            self.$('.o_enable_searchview').toggleClass('o_hidden', !inInbox);
            if (!inInbox && self.searchviewDisplayed) {
                self._toggleSearchView(); // close the searchview when leaving Inbox
            }

            // update Inbox page buttons
            if (inInbox) {
                self.$('.o_mail_chat_mobile_inbox_buttons').removeClass('o_hidden');
                self.$('.o_channel_inbox_item').removeClass('btn-primary').addClass('btn-default');
                self.$('.o_channel_inbox_item[data-type=' + type + ']').removeClass('btn-default').addClass('btn-primary');
            } else {
                self.$('.o_mail_chat_mobile_inbox_buttons').addClass('o_hidden');
            }

            // update bottom buttons
            self.$('.o_mail_mobile_tab').removeClass('active');
            // channel_inbox and channel_starred share the same tab
            type = type === 'channel_starred' ? 'channel_inbox' : type;
            self.$('.o_mail_mobile_tab[data-type=' + type + ']').addClass('active');
        });
    },
    /**
     * @override
     */
    _updateControlPanel: function () {
        this.$buttons.appendTo(this.$('.o_mail_chat_mobile_control_panel'));
        this.searchview.$el.appendTo(this.$('.o_mail_chat_mobile_control_panel'));
        var $enable_searchview = $('<button/>', {type: 'button'})
            .addClass('o_enable_searchview btn fa fa-search')
            .on('click', this._toggleSearchView.bind(this));
        $enable_searchview.insertAfter(this.searchview.$el);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddChannel: function () {
        this.$('.o_mail_add_channel').show().find('input').focus();
    },
    /**
     * Switches to the clicked channel in the Inbox page (Inbox or Starred).
     *
     * @private
     * @param {MouseEvent}
     */
    _onMobileInboxButtonClicked: function (event) {
        this._setChannel(chat_manager.get_channel($(event.currentTarget).data('type')));
        this._updateContent(this.channel.id);
    },
    /**
     * Switches to another tab.
     *
     * @private
     * @param {MouseEvent}
     */
    _onMobileTabClicked: function (event) {
        var type = $(event.currentTarget).data('type');
        if (type === 'channel_inbox') {
            this._setChannel(chat_manager.get_channel('channel_inbox'));
        }
        this._updateContent(type);
    },
    /**
     * Opens a channel in a chat windown (full screen in mobile).
     *
     * @private
     * @param {MouseEvent}
     */
    _onMobileChannelClicked: function (event) {
        var channelId = $(event.currentTarget).data("channel_id");
        chat_manager.detach_channel(chat_manager.get_channel(channelId));
    },
});

});
