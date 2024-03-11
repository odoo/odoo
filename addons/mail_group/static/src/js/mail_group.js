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
        const searchParams = (new URL(document.location.href)).searchParams;
        this.token = searchParams.get('token');
        this.forceUnsubscribe = searchParams.has('unsubscribe');
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
            this.$target.addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
            return false;
        }

        this.$target.removeClass('o_has_error').find('.form-control, .form-select').removeClass('is-invalid');

        const action = (this.isMember || this.forceUnsubscribe) ? 'unsubscribe' : 'subscribe';

        const response = await this._rpc({
            route: '/group/' + action,
            params: {
                'group_id': this.mailgroupId,
                'email': email,
                'token': this.token,
            },
        });

        this.$el.find('.o_mg_alert').remove();

        if (response === 'added') {
            this.isMember = true;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Unsubscribe')).removeClass('btn-primary').addClass('btn-outline-primary');
        } else if (response === 'removed') {
            this.isMember = false;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Subscribe')).removeClass('btn-outline-primary').addClass('btn-primary');
        } else if (response === 'email_sent') {
            // The confirmation email has been sent
            this.$target.html(
                $('<div class="o_mg_alert alert alert-success" role="alert"/>')
                .text(_t('An email with instructions has been sent.'))
            );
        } else if (response === 'is_already_member') {
            this.isMember = true;
            this.$target.find('.o_mg_subscribe_btn').text(_t('Unsubscribe')).removeClass('btn-primary').addClass('btn-outline-primary');
            this.$target.find('.o_mg_subscribe_form').before(
                $('<div class="o_mg_alert alert alert-warning" role="alert"/>')
                .text(_t('This email is already subscribed.'))
            );
        } else if (response === 'is_not_member') {
            if (!this.forceUnsubscribe) {
                this.isMember = false;
                this.$target.find('.o_mg_subscribe_btn').text(_t('Subscribe'));
            }
            this.$target.find('.o_mg_subscribe_form').before(
                $('<div class="o_mg_alert alert alert-warning" role="alert"/>')
                .text(_t('This email is not subscribed.'))
            );
        }

    },
});

return publicWidget.registry.MailGroup;
});
