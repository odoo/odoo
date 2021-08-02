odoo.define('website_mail_group.mail_group', function (require) {
'use strict';

const core = require('web.core');
const _t = core._t;
const MailGroup = require('mail_group.mail_group');

MailGroup.include({
    willStart: async function () {
        await this._super(...arguments);

        // Can not be done in the template of the snippets
        // Because it's rendered only once when the admin add the snippets
        // for the first time, we make a RPC call to setup the widget properly
        const email = (new URL(document.location.href)).searchParams.get('email');
        const response = await this._rpc({
            route: '/groups/is_member',
            params: {
                'group_id': this.$target.data('id'),
                'email': email,
            },
        });

        if (!response) {
            // We do not access to the mail group, just remove the widget
            this.$el.empty();
            return;
        }

        this.$el.removeClass('d-none');

        const userEmail = response.email;
        const isMember = response.is_member;

        if (userEmail && userEmail.length) {
            const emailInput = this.$el.find('.o_mg_subscribe_email');
            emailInput.val(userEmail);
            emailInput.attr('readonly', 1);
        }

        if (isMember) {
            this.$target.find('.o_mg_subscribe_btn').text(_t('Unsubscribe'));
        }

        this.$el.data('isMember', isMember);
    },
});

});
