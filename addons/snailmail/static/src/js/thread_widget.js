odoo.define('snailmail.widget.Thread', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');
var Dialog = require('web.Dialog');

var core = require('web.core');
var _t = core._t;

ThreadWidget.include({

    /**
     * @override
     */
    render: function (thread, options) {
        this._super.apply(this, arguments);
        var messages = _.clone(thread.getMessages({ domain: options.domain || [] }));
        this._messages = messages;
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
            buttons: [{
                text: _t("Re-send letter"),
                classes: 'btn-primary',
                close: true,
                click: (...args) => message.resendLetter(...args),
            }, {
                text: _t("Cancel letter"),
                close: true,
                click: (...args) => message.cancelLetter(...args),
            }, {
                text: _t("Close"),
                close: true,
            }],
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
            buttons: [{
                text: _t("Cancel letter"),
                classes: 'btn-primary',
                close: true,
                click: (...args) => message.cancelLetter(...args),
            }, {
                text: _t("Close"),
                close: true,
            }],
        }).open();
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
     * Discards the generic error handler since more specific handlers are
     * defined here.
     *
     * @override
     */
    _onClickMessageNotificationError(ev) {
        const $target = $(ev.currentTarget);
        if ($target.data('message-type') === 'snailmail') {
            if ($target.data('failure-type') === 'sn_fields') {
                this._onClickMissingRequiredFields(ev);
            }
            if ($target.data('failure-type') === 'sn_credit') {
                this._onClickCreditError(ev);
            }
            if ($target.data('failure-type') === 'sn_trial') {
                this._onClickTrialError(ev);
            }
            if ($target.data('failure-type') === 'sn_price') {
                this._onClickNoPriceAvailable(ev);
            }
            if ($target.data('failure-type') === 'sn_format') {
                this._onClickFormatError(ev);
            }
            if ($target.data('failure-type') === 'sn_error') {
                this._onClickUnknownError(ev);
            }
        } else {
            this._super(...arguments);
        }
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
