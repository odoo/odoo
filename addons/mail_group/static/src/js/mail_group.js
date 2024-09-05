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
        this.mailgroupId = parseInt(this.el.dataset.id);
        this.isMember = this.el.dataset.isMember === "true" || false;
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
            this.el.classList.add("o_has_error");
            [...this.el.querySelectorAll(".form-control, .form-select")].forEach((elem) =>
                elem.classList.add("is-invalid")
            );
            return false;
        }

        this.el.classList.remove("o_has_error");
        [...this.el.querySelectorAll(".form-control, .form-select")].forEach((elem) =>
            elem.classList.remove("is-invalid")
        );

        const action = (this.isMember || this.forceUnsubscribe) ? 'unsubscribe' : 'subscribe';

        const response = await rpc('/group/' + action, {
            'group_id': this.mailgroupId,
            'email': email,
            'token': this.token,
        });

        [...this.el.querySelectorAll(".o_mg_alert")].forEach((elem) => elem.remove());

        const subscribeBtnEl = this.el.querySelector(".o_mg_subscribe_btn");
        if (response === 'added') {
            this.isMember = true;
            subscribeBtnEl.textContent = _t("Unsubscribe");
            subscribeBtnEl.classList.remove("btn-primary");
            subscribeBtnEl.classList.add("btn-outline-primary");
        } else if (response === 'removed') {
            this.isMember = false;
            subscribeBtnEl.textContent = _t("Subscribe");
            subscribeBtnEl.classList.remove("btn-outline-primary");
            subscribeBtnEl.classList.add("btn-primary");
        } else if (response === 'email_sent') {
            // The confirmation email has been sent
            this.el.outerHTML = `<div class="o_mg_alert alert alert-success" role="alert">${_t(
                "An email with instructions has been sent."
            )}</div>`;
        } else if (response === 'is_already_member') {
            this.isMember = true;
            subscribeBtnEl.textContent = _t("Unsubscribe");
            subscribeBtnEl.classList.remove("btn-primary");
            subscribeBtnEl.classList.add("btn-outline-primary");
            const alertEl = document.createElement("div");
            alertEl.setAttribute("class", "o_mg_alert alert alert-warning");
            alertEl.setAttribute("role", "alert");
            alertEl.textContent = _t("This email is already subscribed.");
            document.insertBefore(alertEl, this.el.querySelector(".o_mg_subscribe_form"));
        } else if (response === 'is_not_member') {
            if (!this.forceUnsubscribe) {
                this.isMember = false;
                subscribeBtnEl.textContent = _t("Subscribe");
            }
            const alertEl = document.createElement("div");
            alertEl.setAttribute("class", "o_mg_alert alert alert-warning");
            alertEl.setAttribute("role", "alert");
            alertEl.textContent = _t("This email is not subscribed.");
            document.insertBefore(alertEl, this.el.querySelector(".o_mg_subscribe_form"));
        }
    },
});

export default publicWidget.registry.MailGroup;
