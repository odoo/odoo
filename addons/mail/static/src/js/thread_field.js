odoo.define('mail.ThreadField', function (require) {
"use strict";

var CreateModeDocumentThread = require('mail.model.CreateModeDocumentThread');
var ThreadWidget = require('mail.widget.Thread');

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var concurrency = require('web.concurrency');

var _t = core._t;

/**
 * 'mail_thread' widget: displays the thread of messages
 */
var ThreadField = AbstractField.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        // Used to automatically mark document thread as read at the moment we
        // access the document and render the thread.
        this._markAsReadOnNextRender = false;
        this._setDocumentThread();
    },
    /**
     * @override
     */
    willStart: function () {
        return this.alive(this.call('mail_service', 'isReady'));
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.dp = new concurrency.DropPrevious();

        this._threadWidget = new ThreadWidget(this, {
            displayOrder: ThreadWidget.ORDER.DESC,
            displayDocumentLinks: false,
            displayMarkAsRead: false,
            squashCloseMessages: false,
        });

        this._threadWidget.on('load_more_messages', this, this._onLoadMoreMessages);
        this._threadWidget.on('redirect', this, this._onRedirect);
        this._threadWidget.on('redirect_to_channel', this, this._onRedirectToChannel);
        this._threadWidget.on('toggle_star_status', this, function (messageID) {
            var message = self.call('mail_service', 'getMessage', messageID);
            message.toggleStarStatus();
        });

        var def1 = this._threadWidget.appendTo(this.$el);
        var def2 = this._super.apply(this, arguments);

        return this.alive($.when(def1, def2)).then(function () {
            // unwrap the thread to remove an unnecessary level on div
            self.setElement(self._threadWidget.$el);
            var mailBus = self.call('mail_service', 'getMailBus');
            mailBus.on('new_message', self, self._onNewMessage);
            mailBus.on('update_message', self, self._onUpdateMessage);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {integer[]} attachmentIDs
     */
    removeAttachments: function (attachmentIDs) {
        this._documentThread.removeAttachmentsFromMessages(attachmentIDs);
    },
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
        return this._documentThread.postMessage(message)
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
        if (!this._documentThread) {
            var thread = new CreateModeDocumentThread();
            options = { isCreateMode: true };
            self._threadWidget.render(thread, options);
            return $.when();
        } else {
            var fetchDef = this.dp.add(this._documentThread.fetchMessages(options));
            return fetchDef.then(function () {
                self._threadWidget.render(self._documentThread, {
                    displayLoadMore: self._documentThread.getMessages().length < self._documentThread.getMessageIDs().length,
                });
                if (self._markAsReadOnNextRender) {
                    self._markAsReadOnNextRender = false;
                    return self._documentThread.markAsRead();
                }
            });
        }
    },
    /**
     * @override
     * @private
     * @returns {$.Deferred}
     */
    _render: function () {
        return this._fetchAndRenderThread();
    },
    /**
     * The mail widget being persistent, one needs to update the res_id and
     * to set the correct DocumentThread on reset.
     *
     * @override
     * @private
     * @param {any} record
     */
    _reset: function (record) {
        this._super.apply(this, arguments);
        this.res_id = record.res_id;
        this._setDocumentThread();
    },
    /**
     * Sets this._documentThread, the DocumentThread associated with the current
     * model and resID.
     *
     * If it is a new document in create mode, unset the document thread.
     */
    _setDocumentThread: function () {
        var params = {
            messageIDs: this.value.res_ids,
            name: this.recordData.display_name,
            resID: this.res_id,
            resModel: this.model,
        };
        if (!params.resID) {
            this._documentThread = null;
        } else {
            this._documentThread = this.call('mail_service', 'getOrAddDocumentThread', params);
            this._markAsReadOnNextRender = true;
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
        if (
            message.isLinkedToDocumentThread() &&
            message.getDocumentModel() === this.model &&
            message.getDocumentID() === this.res_id
        ) {
            this.trigger_up('new_message', {
                id: this.value.id,
                messageIDs: this._documentThread.getMessageIDs(),
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
        this.call('mail_service', 'joinChannel', channelID).then(function () {
            // Execute Discuss with 'channel' as default channel
            self.do_action('mail.action_discuss', { active_id: channelID });
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
        if (
            message.isLinkedToDocumentThread() &&
            message.getDocumentModel() === this.model &&
            message.getDocumentID() === this.res_id
        ) {
            this._fetchAndRenderThread();
        }
    },
});

field_registry.add('mail_thread', ThreadField);

return ThreadField;

});
