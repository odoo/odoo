odoo.define('sms.widget.Thread', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');
var core = require('web.core');

var QWeb = core.qweb;

ThreadWidget.include({
    events: _.extend({}, ThreadWidget.prototype.events, {
        'click .o_thread_message_sms_error': '_onClickSMSError'
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
        var messages = _.clone(thread.getMessages({domain: options.domain || []}));
        this._renderMessageSmsPopover(messages);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the popover when mouse-hovering on the mail icon of a message
     * in the thread. There is at most one such popover at any given time.
     *
     * @private
     * @param {mail.model.AbstractMessage[]} messages list of messages in the
     *   rendered thread, for which popover on mouseover interaction is
     *   permitted.
     */
    _renderMessageSmsPopover: function (messages) {
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
                var message = _.find(messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('sms.widget.Thread.Message.SmsTooltip', {
                    data: message.getSmsIds()
                });
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSMSError: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.do_action('sms.sms_resend_action', {
            additional_context: {
                default_mail_message_id: messageID
            }
        });
    },
});
});
