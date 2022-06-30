/** @odoo-module **/

import concurrency from 'web.concurrency';
import core from 'web.core';
import session from 'web.session';
import utils from 'web.utils';
import Widget from 'web.Widget';

const _t = core._t;
/*
 * Rating for Livechat
 *
 * This widget displays the 3 rating smileys, and a textarea to add a reason
 * (only for red smiley), and sends the user feedback to the server.
 */
const Feedback = Widget.extend({
    template: 'im_livechat.legacy.im_livechat.FeedBack',

    events: {
        'click .o_livechat_rating_choices img': '_onClickSmiley',
        'click .o_livechat_no_feedback span': '_onClickNoFeedback',
        'click .o_rating_submit_button': '_onClickSend',
        'click .o_email_chat_button': '_onEmailChat',
        'click .o_livechat_email_error .alert-link': '_onTryAgain',
    },

    /**
     * @param {?} parent
     * @param {Messaging} messaging
     * @param {@im_livechat/legacy/models/public_livechat} livechat
     */
    init(parent, messaging, livechat) {
        this._super(parent);
        this.messaging = messaging;
        this.server_origin = session.origin;
        this.rating = undefined;
        this.dp = new concurrency.DropPrevious();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} options
     */
     _sendFeedback(reason) {
        const args = {
            uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
            rate: this.rating,
            reason,
        };
        this.dp.add(session.rpc('/im_livechat/feedback', args)).then((response) => {
            const emoji = this.messaging.publicLivechatGlobal.RATING_TO_EMOJI[this.rating] || "??";
            let content;
            if (!reason) {
                content = utils.sprintf(_t("Rating: %s"), emoji);
            }
            else {
                content = "Rating reason: \n" + reason;
            }
            this.trigger('send_message', { content, isFeedback: true });
        });
    },
    /**
    * @private
    */
    _showThanksMessage() {
        this.$('.o_livechat_rating_box').empty().append($('<div />', {
            text: _t('Thank you for your feedback'),
            class: 'text-muted'
        }));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickNoFeedback() {
        this.trigger('feedback_sent'); // will close the chat
    },
    /**
     * @private
     */
    _onClickSend() {
        this.$('.o_livechat_rating_reason').hide();
        this._showThanksMessage();
        if (_.isNumber(this.rating)) {
            this._sendFeedback(this.$('textarea').val());
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSmiley(ev) {
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.o_livechat_rating_choices img').removeClass('selected');
        this.$('.o_livechat_rating_choices img[data-value="' + this.rating + '"]').addClass('selected');

        // only display textearea if bad smiley selected
        if (this.rating !== 5) {
            this._sendFeedback();
            this.$('.o_livechat_rating_reason').show();
        } else {
            this.$('.o_livechat_rating_reason').hide();
            this._showThanksMessage();
            this._sendFeedback();
        }
    },
    /**
    * @private
    */
    _onEmailChat() {
        const $email = this.$('#o_email');

        if (utils.is_email($email.val())) {
            $email.removeAttr('title').removeClass('is-invalid').prop('disabled', true);
            this.$('.o_email_chat_button').prop('disabled', true);
            this._rpc({
                route: '/im_livechat/email_livechat_transcript',
                params: {
                    uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
                    email: $email.val(),
                }
            }).then(() => {
                this.$('o_livechat_email_sentLabel').show();
                this.$('o_livechat_email_receiveCopyLabel').hide();
                this.$('o_livechat_email_receiveCopyForm').hide();
            }).guardedCatch(() => {
                this.$('.o_livechat_email').hide();
                this.$('.o_livechat_email_error').show();
            });
        } else {
            $email.addClass('is-invalid').prop('title', _t('Invalid email address'));
        }
    },
    /**
    * @private
    */
    _onTryAgain() {
        this.$('#o_email').prop('disabled', false);
        this.$('.o_email_chat_button').prop('disabled', false);
        this.$('.o_livechat_email_error').hide();
        this.$('.o_livechat_email').show();
    },
});

export default Feedback;
