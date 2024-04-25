/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.MailGroup = publicWidget.Widget.extend({
    selector: '.o_mail_group',
    events: {
        'click .o_mg_subscribe_btn': '_onSubscribeBtnClick',
    },

    /**
     * @override
     */
    start: function () {
        this.mailgroupId = this.$el.data('id');
        this.isMember = this.$el.data('isMember') || false;
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
        const emailElem = this.el.querySelector(".o_mg_subscribe_email");
        const email = emailElem.value;

        if (!email.match(/.+@.+/)) {
            this.el.classList.add('o_has_error');
            [...this.el.querySelectorAll('.form-control, .form-select')].forEach((elem) => elem.classList.add('is-invalid'));
            return false;
        }

        this.el.classList.remove('o_has_error');
        [...this.el.querySelectorAll('.form-control, .form-select')].forEach((elem) => elem.classList.remove('is-invalid'));

        const action = (this.isMember || this.forceUnsubscribe) ? 'unsubscribe' : 'subscribe';

        const response = await rpc('/group/' + action, {
            'group_id': this.mailgroupId,
            'email': email,
            'token': this.token,
        });

        [...this.el.querySelectorAll('.o_mg_alert')].forEach(elem => elem.remove());

        if (response === 'added') {
            this.isMember = true;
            const subscribeBtns = this.el.querySelectorAll('.o_mg_subscribe_btn');
            subscribeBtns.forEach(elem => {
                elem.textContent = _t('Unsubscribe');
                elem.classList.remove('btn-primary');
                elem.classList.add('btn-outline-primary');
            });
        } else if (response === 'removed') {
            this.isMember = false;
            const subscribeBtns = this.el.querySelectorAll('.o_mg_subscribe_btn');
            subscribeBtns.forEach(elem => {
                elem.textContent = _t('Subscribe');
                elem.classList.remove('btn-outline-primary');
                elem.classList.add('btn-primary');
            });
        } else if (response === 'email_sent') {
            // The confirmation email has been sent
            this.el.outerHTML = `<div class="o_mg_alert alert alert-success" role="alert">${_t('An email with instructions has been sent.')}</div>`;
        } else if (response === 'is_already_member') {
            this.isMember = true;
            const subscribeBtns = this.el.querySelectorAll('.o_mg_subscribe_btn');
            subscribeBtns.forEach(elem => {
                elem.textContent = _t('Unsubscribe');
                elem.classList.remove('btn-primary');
                elem.classList.add('btn-outline-primary');
            });
            const alertElement = document.createElement('div');
            alertElement.setAttribute('class', 'o_mg_alert alert alert-warning');
            alertElement.setAttribute('role', 'alert');
            alertElement.textContent = _t('This email is already subscribed.');
            document.insertBefore(alertElement, this.el.querySelector('.o_mg_subscribe_form'));
        } else if (response === 'is_not_member') {
            if (!this.forceUnsubscribe) {
                this.isMember = false;
                [...this.el.querySelectorAll('.o_mg_subscribe_btn')].forEach(elem => elem.textContent = _t('Subscribe'));
            }
            const alertElement = document.createElement('div');
            alertElement.setAttribute('class', 'o_mg_alert alert alert-warning');
            alertElement.setAttribute('role', 'alert');
            alertElement.textContent = _t('This email is not subscribed.');
            document.insertBefore(alertElement, this.el.querySelector('.o_mg_subscribe_form'));
        }
    },
});

export default publicWidget.registry.MailGroup;
