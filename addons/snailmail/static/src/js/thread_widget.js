odoo.define('snailmail.widget.Thread', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');
var Dialog = require('web.Dialog');

var core = require('web.core');
var QWeb = core.qweb;
var _t = core._t;

ThreadWidget.include({
    dependencies: ['bus_service'],
    events: _.extend({}, ThreadWidget.prototype.events, {
        'click .o_thread_message_snailmail_missing_required_fields': '_onClickMissingRequiredFields',
        'click .o_thread_message_snailmail_credit_error': '_onClickCreditError',
        'click .o_thread_message_snailmail_trial_error': '_onClickTrialError',
        'click .o_thread_message_snailmail_no_price_available': '_onClickNoPriceAvailable',
        'click .o_thread_message_snailmail_format_error': '_onClickFormatError',
        'click .o_thread_message_snailmail_unknown_error': '_onClickUnknownError',
    }),
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._enabledOptions = _.defaults(this._enabledOptions, {
            displaySnailmailIcons: true,
        });
        this._disabledOptions = _.defaults(this._disabledOptions, {
            displaySnailmailIcons: false,
        });
    },
    /**
     * @override
     */
    render: function (thread, options) {
        this._super.apply(this, arguments);
        var messages = _.clone(thread.getMessages({ domain: options.domain || [] }));
        this._messages  = messages;
        this._renderMessageSnailmailPopover();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {integer} messageID 
     * @param {string} content 
     */
    _openCreditErrorDialog: function (messageID, content) {
        var message = _.find(this._messages, function (message) {
            return message.getID() === messageID;
        });
        new Dialog(this, {
            size: 'medium',
            title: _t("Failed letter"),
            $content: $('<div>').html(content),
            buttons: [
                {text: _t("Re-send letter"), classes: 'btn-primary', close: true, click: _.bind(message.resendLetter, message)},
                {text: _t("Cancel letter"), close: true, click: _.bind(message.cancelLetter, message)},
                {text: _t("Close"), close: true},
            ],
        }).open();
    },
    /**
     * @private
     * @param {integer} messageID 
     * @param {string} content 
     */
    _openGenericErrorDialog: function (messageID, content) {
        var message = _.find(this._messages, function (message) {
            return message.getID() === messageID;
        });
        new Dialog(this, {
            size: 'medium',
            title: _t("Failed letter"),
            $content: $('<div>').html(content),
            buttons: [
                {text: _t("Cancel letter"), classes: 'btn-primary', close: true, click: _.bind(message.cancelLetter, message)},
                {text: _t("Close"), close: true},
            ],
        }).open();
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
    _renderMessageSnailmailPopover: function () {
        var self = this;
        if (this._messageSnailmailPopover) {
            this._messageSnailmailPopover.popover('hide');
        }
        if (!this.$('.o_thread_snailmail_tooltip').length) {
            return;
        }
        this._messageSnailmailPopover = this.$('.o_thread_snailmail_tooltip').popover({
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
                return QWeb.render('snailmail.widget.Thread.Message.SnailmailTooltip', {
                    status: message.getSnailmailStatus()
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
    _onClickCreditError: function (ev) {
        var self = this;
        var messageID = $(ev.currentTarget).data('message-id');
        this._rpc({
            model: 'iap.account',
            method: 'get_credits_url',
            args: ['snailmail'],
        }).then(function (link) {
            var content = _.str.sprintf(_t(
                '<p>The letter could not be sent due to insufficient credits on your IAP account.</p>' +
                '<div class= "text-right">' +
                '<a class="btn btn-link buy_credits" href=%s target="_blank">' +
                '<i class= "fa fa-arrow-right"/> Buy credits' +
                '</a>' +
                '</div>'
            ), link);
            self._openCreditErrorDialog(messageID, content);
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickFormatError: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.do_action('snailmail.snailmail_letter_format_error_action', {
            additional_context: {
                message_id: messageID,
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickMissingRequiredFields: function (ev) {
        var self = this;

        var messageID = $(ev.currentTarget).data('message-id');
        var domain = [['message_id', '=', messageID]];
        this._rpc({
            model: 'snailmail.letter',
            method: 'search',
            args: [domain],
        }).then(function (letterIds) {
            self.do_action('snailmail.snailmail_letter_missing_required_fields_action', {
                additional_context: {
                    letter_id: letterIds[0]
                },
                on_close: function () {
                    self.trigger_up('reload');
                }
            });
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickNoPriceAvailable: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        var content = _t('<p>The country to which you want to send the letter is not supported by our service.</p>');
        this._openGenericErrorDialog(messageID, content);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickTrialError: function (ev) {
        var self = this;
        var messageID = $(ev.currentTarget).data('message-id');
        this._rpc({
            model: 'iap.account',
            method: 'get_credits_url',
            args: ['snailmail', '', 0, true],
        }).then(function (link) {
            var content = _.str.sprintf(_t(
                '<p>You need credits on your IAP account to send a letter.</p>' +
                '<div class= "text-right">' +
                '<a class="btn btn-link buy_credits" href=%s>' +
                '<i class= "fa fa-arrow-right"/> Buy credits' +
                '</a>' +
                '</div>'
            ), link);
            self._openCreditErrorDialog(messageID, content);
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickUnknownError: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        var content = _t('<p>An unknown error occured. Please contact our <a href="https://www.odoo.com/help" target="new">support</a> for further assistance.</p>');
        this._openGenericErrorDialog(messageID, content);
    },
});

});
