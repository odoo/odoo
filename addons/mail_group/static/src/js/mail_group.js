odoo.define('mail_group.mail_group', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const core = require('web.core');
const _t = core._t;

publicWidget.registry.MailGroup = publicWidget.Widget.extend({
    selector: '.o_mail_group',
    events: {
        'click .o_mg_subscribe_btn': '_onSubscribeBtnClick',
    },

    /**
     * @override
     */
    start: function () {
        this.mailgroupId = this.$target.data('id');
        this.isMember = this.$target.data('isMember') || false;
        this.token = (new URL(document.location.href)).searchParams.get('token');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubscribeBtnClick: async function (ev) {
        ev.preventDefault();
        const $email = this.$target.find(".o_mg_subscribe_email");
        const email = $email.val();

        if (!email.match(/.+@.+/)) {
            this.$target.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return false;
        }

        this.$target.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

        let action = this.isMember ? 'unsubscribe' : 'subscribe';

        const response = await this._rpc({
            route: '/groups/subscription',
            params: {
                'group_id': this.mailgroupId,
                'action': action,
                'email': email,
                'token': this.token,
            },
        });

        this.$el.find('.o_mg_alert').remove();

        if (response === 'added') {
            this.isMember = true;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Unsubscribe'));
        } else if (response === 'removed') {
            this.isMember = false;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Subscribe'));
        } else if (response === 'email_sent') {
            // The confirmation email has been sent
            this.$target.html(
                $('<div class="o_mg_alert alert alert-success" role="alert"/>')
                .text(_t('An email with the instructions has been sent.'))
            );
        } else if (response === 'is_already_member') {
            this.isMember = true;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Unsubscribe'));
            this.$target.find('.o_mg_subscribe_form').before(
                $('<div class="o_mg_alert alert alert-warning" role="alert"/>')
                .text(_t('This email is already subscribed.'))
            );
        } else if (response === 'is_not_member') {
            this.isMember = false;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Subscribe'));
            this.$target.find('.o_mg_subscribe_form').before(
                $('<div class="o_mg_alert alert alert-warning" role="alert"/>')
                .text(_t('This email is not subscribed.'))
            );
        }

    },
});

return publicWidget.registry.MailGroup;
});
