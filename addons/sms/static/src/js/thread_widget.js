odoo.define('sms.widget.Thread', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');
var Dialog = require('web.Dialog');

var core = require('web.core');
var QWeb = core.qweb;
var _t = core._t;

ThreadWidget.include({
    dependencies: ['bus_service'],
    events: _.extend({}, ThreadWidget.prototype.events, {
        'click .o_thread_message_sms_missing_number': '_onClickMissingNumberError',
        'click .o_thread_message_sms_wrong_number_format': '_onClickWrongNumberFormatError',
        'click .o_thread_message_sms_insufficient_credit': '_onClickInsufficientCreditError',
    }),
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._enabledOptions = _.defaults(this._enabledOptions, {
            displaySmsIcons: true,
        });
        this._disabledOptions = _.defaults(this._disabledOptions, {
            displaySmsIcons: false,
        });
    },
    /**
     * @override
     */
    render: function (thread, options) {
        this._super.apply(this, arguments);
        var messages = _.clone(thread.getMessages({ domain: options.domain || [] }));
        this._messages = messages;
        this._renderMessageSmsPopover();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {integer} messageID
     * @param {string} content
     */
    _openErrorDialog: function (messageID, content) {
        var message = _.find(this._messages, function (message) {
            return message.getID() === messageID;
        });
        new Dialog(this, {
            size: 'medium',
            title: _t("Failed SMS"),
            $content: $('<div>').html(content),
            buttons: [
                {text: _t("Re-send SMS"), classes: 'btn-primary', close: true, click: _.bind(message.resendSms, message)},
                {text: _t("Cancel SMS"), close: true, click: _.bind(message.cancelSms, message)},
                {text: _t("Close"), close: true},
            ],
        }).open();
    },

    /**
     * @private
     */
    _openNumberErrorDialog: function(ev) {
        var self = this;

        var messageID = $(ev.currentTarget).data('message-id');
        var domain = [['message_id', '=', messageID]];
        this._rpc({
            model: 'sms.sms',
            method: 'search',
            args: [domain],
        }).then(function (smsIds) {
            self.do_action('sms.sms_resend_action', {
                additional_context: {
                    sms_id: smsIds[0]
                },
                on_close: function () {
                    self.trigger_up('reload');
                }
            });
        });
    },

    /**
     * Render the popover when mouse-hovering on the mail icon of a message
     * in the thread. There is at most one such popover at any given time.
     *
     * @private
     * @param {mail.model.AbstractMessage[]} messages list of messages in the
     *   rendered thread, for which popover on mouseover interaction is
     *   permitted.
     */
    _renderMessageSmsPopover: function () {
        var self = this;
        if (this._messageSmsPopover) {
            this._messageSmsPopover.popover('hide');
        }
        if (!this.$('.o_thread_sms_tooltip').length) {
            return;
        }

        this._messageSmsPopover = this.$('.o_thread_sms_tooltip').popover({
            html: true,
            boundary: 'viewport',
            placement: 'auto',
            trigger: 'hover',
            offset: '0, 1',
            content: function () {
                var messageID = $(this).data('message-id');
                var message = _.find(self._messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('sms.widget.Thread.Message.SmsTooltip', {
                    recipient: message.getDocumentName(),
                    status: message.getSmsStatus()
                });
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickMissingNumberError: function(ev) {
        this._openNumberErrorDialog(ev);
    },

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickWrongNumberFormatError: function(ev) {
        this._openNumberErrorDialog(ev);
    },

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickInsufficientCreditError: function(ev) {
        var self = this;
        var messageID = $(ev.currentTarget).data('message-id');
        this._rpc({
            model: 'iap.account',
            method: 'get_credits_url',
            args: ['sms'],
        }).then(function(link) {
            var content = _.str.sprintf(_t(
                '<p>The SMS text message could not be sent due to insufficient credits on your IAP account.</p>' +
                '<div class= "text-right">' +
                '<a class="btn btn-link buy_credits" href=%s>' +
                '<i class= "fa fa-arrow-right"/> Buy credits' +
                '</a>' +
                '</div>'
            ), link);
            self._openErrorDialog(messageID, content);
        });
    },
});

});
