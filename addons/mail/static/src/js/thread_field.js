odoo.define('mail.ThreadField', function (require) {
"use strict";

var ChatThread = require('mail.ChatThread');

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var concurrency = require('web.concurrency');
var session = require('web.session');

var _t = core._t;

// -----------------------------------------------------------------------------
// 'mail_thread' widget: displays the thread of messages
// -----------------------------------------------------------------------------
var ThreadField = AbstractField.extend({
    // inherited
    init: function () {
        this._super.apply(this, arguments);
        this.msgIDs = this.value.res_ids;
    },
    willStart: function () {
        var chatReady = this.call('chat_manager', 'isReady');
        return this.alive(chatReady);
    },
    start: function () {
        var self = this;

        this.dp = new concurrency.DropPrevious();

        this.thread = new ChatThread(this, {
            display_order: ChatThread.ORDER.DESC,
            display_document_link: false,
            display_needactions: false,
            squash_close_messages: false,
        });

        this.thread.on('load_more_messages', this, this._onLoadMoreMessages);
        this.thread.on('redirect', this, this._onRedirect);
        this.thread.on('redirect_to_channel', this, this._onRedirectToChannel);
        this.thread.on('toggle_star_status', this, function (messageID) {
            self.call('chat_manager', 'toggleStarStatus', messageID);
        });

        var def1 = this.thread.appendTo(this.$el);
        var def2 = this._super.apply(this, arguments);

        return this.alive($.when(def1, def2)).then(function () {
            // unwrap the thread to remove an unnecessary level on div
            self.setElement(self.thread.$el);
            var chatBus = self.call('chat_manager', 'getChatBus');
            chatBus.on('new_message', self, self._onNewMessage);
            chatBus.on('update_message', self, self._onUpdateMessage);
        });
    },
    _render: function () {
        return this._fetchAndRenderThread(this.msgIDs);
    },
    isSet: function () {
        return true;
    },
    destroy: function () {
        this.call('chat_manager', 'removeChatterMessages', this.model);
        this._super.apply(this, arguments);
    },
    _reset: function (record) {
        this._super.apply(this, arguments);
        this.msgIDs = this.value.res_ids;
        // the mail widgets being persistent, one need to update the res_id on reset
        this.res_id = record.res_id;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param  {Object} message
     * @param  {integer[]} message.partner_ids
     * @return {Deferred}
     */
    postMessage: function (message) {
        var self = this;
        var options = {model: this.model, res_id: this.res_id};
        return this.call('chat_manager', 'postMessage', message, options)
            .then(function () {
                if (message.partner_ids.length) {
                    self.trigger_up('reload_mail_fields', {followers: true});
                }
            })
            .fail(function () {
                self.do_notify(_t('Sending Error'), _t('Your message has not been sent.'));
            });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Object[]} an array containing a single message 'Creating a new record...'
     */
    _forgeCreationModeMessages: function () {
        return [{
            id: 0,
            body: "<p>Creating a new record...</p>",
            date: moment(),
            author_id: [session.partner_id, session.partner_display_name],
            displayed_author: session.partner_display_name,
            avatar_src: "/web/image/res.partner/" + session.partner_id + "/image_small",
            attachment_ids: [],
            customer_email_data: [],
            tracking_value_ids: [],
        }];
    },
    /**
     * @private
     * @param {integer[]} ids
     * @param {Object} [options]
     */
    _fetchAndRenderThread: function (ids, options) {
        var self = this;
        options = options || {};
        options.ids = ids;
        var fetch_def = this.dp.add(this.call('chat_manager', 'getMessages', options));
        return fetch_def.then(function (raw_messages) {
            var isCreateMode = false;
            if (!self.res_id) {
                raw_messages = self._forgeCreationModeMessages();
                isCreateMode = true;
            }
            self.thread.render(raw_messages, {
                display_load_more: raw_messages.length < ids.length,
                isCreateMode: isCreateMode,
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When a new message arrives, fetch its data to render it
     * @param {Number} message_id : the identifier of the new message
     * @returns {Deferred}
     */
    _onLoadMoreMessages: function () {
        this._fetchAndRenderThread(this.msgIDs, {forceFetch: true});
    },
    _onNewMessage: function (message) {
        if (message.model === this.model && message.res_id === this.res_id) {
            this.msgIDs.unshift(message.id);
            this.trigger_up('new_message', {
                id: this.value.id,
                msgIDs: this.msgIDs,
            });
            this._fetchAndRenderThread(this.msgIDs);
        }
    },
    _onRedirectToChannel: function (channelID) {
        var self = this;
        this.call('chat_manager', 'joinChannel', channelID).then(function () {
            // Execute Discuss client action with 'channel' as default channel
            self.do_action('mail.mail_channel_action_client_chat', {active_id: channelID});
        });
    },
    _onRedirect: function (res_model, res_id) {
        this.trigger_up('redirect', {
            res_id: res_id,
            res_model: res_model,
        });
    },
    _onUpdateMessage: function (message) {
        if (message.model === this.model && message.res_id === this.res_id) {
            this._fetchAndRenderThread(this.msgIDs);
        }
    },
});

field_registry.add('mail_thread', ThreadField);

return ThreadField;

});
