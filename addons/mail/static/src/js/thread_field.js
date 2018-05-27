odoo.define('mail.ThreadField', function (require) {
"use strict";

var Message = require('mail.model.Message');
var ThreadWidget = require('mail.widget.Thread');

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var concurrency = require('web.concurrency');
var session = require('web.session');

var _t = core._t;

/**
 * 'mail_thread' widget: displays the thread of messages
 */
var ThreadField = AbstractField.extend({
    init: function () {
        this._super.apply(this, arguments);
        this._messageIDs = this.value.res_ids; // used for updating the record's datapoint on received msgs
    },
    willStart: function () {
        return this.alive(this.call('chat_service', 'isReady'));
    },
    start: function () {
        var self = this;

        this.dp = new concurrency.DropPrevious();

        this._threadWidget = new ThreadWidget(this, {
            displayOrder: ThreadWidget.ORDER.DESC,
            displayDocumentLink: false,
            displayMarkAsRead: false,
            squashCloseMessages: false,
        });

        this._threadWidget.on('load_more_messages', this, this._onLoadMoreMessages);
        this._threadWidget.on('redirect', this, this._onRedirect);
        this._threadWidget.on('redirect_to_channel', this, this._onRedirectToChannel);
        this._threadWidget.on('toggle_star_status', this, function (messageID) {
            var message = self.call('chat_service', 'getMessage', messageID);
            message.toggleStarStatus();
        });

        var def1 = this._threadWidget.appendTo(this.$el);
        var def2 = this._super.apply(this, arguments);

        return this.alive($.when(def1, def2)).then(function () {
            // unwrap the thread to remove an unnecessary level on div
            self.setElement(self._threadWidget.$el);
            var chatBus = self.call('chat_service', 'getChatBus');
            chatBus.on('new_message', self, self._onNewMessage);
            chatBus.on('update_message', self, self._onUpdateMessage);
        });
    },
    destroy: function () {
        this.call('chat_service', 'removeChatterMessages', this.model);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @return {boolean}
     */
    isSet: function () {
        return true;
    },
    /**
     * @param  {Object} message
     * @param  {integer[]} message.partner_ids
     * @return {$.Promise}
     */
    postMessage: function (message) {
        var self = this;
        var options = { model: this.model, resID: this.res_id };
        return this.call('chat_service', 'postMessage', message, options)
            .then(function () {
                if (message.partner_ids.length) {
                    self.trigger_up('reload_mail_fields', { followers: true });
                }
            })
            .fail(function () {
                self.do_notify(_t("Sending Error"), _t("Your message has not been sent."));
            });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} [options]
     * @param {boolean} [options.forceFetch]
     * @return {$.Deferred}
     */
    _fetchAndRenderThread: function (options) {
        var self = this;
        options = options || {};
        options.ids = this._messageIDs;
        // var fetchDef = this.dp.add(this.call('chat_service', 'getMessages', options));
        var documentChat = this.call('chat_service', 'getDocumentChat', this.model, this.res_id);
        if (!documentChat) {
            documentChat = this.call('chat_service', 'addDocumentChat', this.model, this.res_id);
        }
        documentChat.setMessageIDs(this._messageIDs);
        var fetchDef = this.dp.add(documentChat.getMessages(options));
        return fetchDef.then(function (rawMessages) {
            var isCreateMode = false;
            if (!self.res_id) {
                rawMessages = self._forgeCreateMessages();
                isCreateMode = true;
            }
            self._threadWidget.render(rawMessages, {
                displayLoadMore: rawMessages.length < self._messageIDs.length,
                isCreateMode: isCreateMode,
            });
        });
    },
    /**
     * Make a fake list of messages to render in create mode.
     * Instead of rendering no messages at all, it displays a single message
     * with body content "Creating a new record".
     *
     * @private
     * @returns {mail.model.Message[]} an array containing a single message 'Creating a new record...'
     */
    _forgeCreateMessages: function () {
        var createMessage = new Message(this, {
            id: 0,
            body: _t("<p>Creating a new record...</p>"),
            author_id: [session.partner_id, session.partner_display_name],
        });
        return [createMessage];
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        return this._fetchAndRenderThread();
    },
    /**
     * @override
     * @private
     * @param {any} record
     */
    _reset: function (record) {
        this._super.apply(this, arguments);
        this._messageIDs = this.value.res_ids;
        // the mail widgets being persistent, one need to update the res_id on reset
        this.res_id = record.res_id;
        // update msgIDs of the document chat
        var documentChat = this.call('chat_service', 'getDocumentChat', this.model, this.res_id);
        if (documentChat) {
            documentChat.setMessageIDs(this._messageIDs);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When a new message arrives, fetch its data to render it
     *
     * @private
     */
    _onLoadMoreMessages: function () {
        this._fetchAndRenderThread({ forceFetch: true });
    },
    /**
     * @private
     * @param {mail.model.Message}
     */
    _onNewMessage: function (message) {
        if (message.getDocumentModel() === this.model && message.getDocumentResID() === this.res_id) {
            this._messageIDs.unshift(message.getID());
            this.trigger_up('new_message', {
                id: this.value.id,
                messageIDs: this._messageIDs,
            });
            this._fetchAndRenderThread();
        }
    },
    /**
     * @private
     * @param {integer} channelID
     */
    _onRedirectToChannel: function (channelID) {
        var self = this;
        this.call('chat_service', 'joinChannel', channelID).then(function () {
            // Execute Discuss client action with 'channel' as default channel
            self.do_action('mail.mail_channel_action_client_chat', { active_id: channelID });
        });
    },
    /**
     * @private
     * @param {string} resModel
     * @param {integer} resID
     */
    _onRedirect: function (resModel, resID) {
        this.trigger_up('redirect', {
            res_id: resID,
            res_model: resModel,
        });
    },
    /**
     * @private
     * @param {mail.model.Message}
     */
    _onUpdateMessage: function (message) {
        if (message.getDocumentModel() === this.model && message.getDocumentResID() === this.res_id) {
            this._fetchAndRenderThread();
        }
    },
});

field_registry.add('mail_thread', ThreadField);

return ThreadField;

});
