/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import MailGroup from "@mail_group/js/mail_group";

MailGroup.include({
    start: async function () {
        await this._super(...arguments);

        // Can not be done in the template of the snippets
        // Because it's rendered only once when the admin add the snippets
        // for the first time, we make a RPC call to setup the widget properly
        const email = (new URL(document.location.href)).searchParams.get('email');
        const response = await this.rpc('/group/is_member', {
            'group_id': this.mailgroupId,
            'email': email,
            'token': this.token,
        });

        if (!response) {
            // We do not access to the mail group, just remove the widget
            this.$el.empty();
            return;
        }

        this.$el.removeClass('d-none');

        const userEmail = response.email;
        this.isMember = response.is_member;

        if (userEmail && userEmail.length) {
            const emailInput = this.$el.find('.o_mg_subscribe_email');
            emailInput.val(userEmail);
            emailInput.attr('readonly', 1);
        }

        if (this.isMember) {
            this.$el.find('.o_mg_subscribe_btn').text(_t('Unsubscribe')).removeClass('btn-primary').addClass('btn-outline-primary');
        }

        this.$el.data('isMember', this.isMember);
    },
    /**
     * @override
     */
    destroy: function () {
        this.el.classList.add('d-none');
        this._super(...arguments);
    },
});

// TODO should probably have a better way to handle this, maybe the invisible
// block system could be extended to handle this kind of things. Here we only
// do the same as the non-edit mode public widget: showing and hiding the widget
// but without the rest. Arguably could just enable the whole widget in edit
// mode but not stable-friendly.
publicWidget.registry.MailGroupEditMode = publicWidget.Widget.extend({
    selector: MailGroup.prototype.selector,
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        if (this.editableMode) {
            this.el.classList.remove('d-none');
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.editableMode) {
            this.el.classList.add('d-none');
        }
        this._super(...arguments);
    },
});
