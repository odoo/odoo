import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class MailGroup extends Interaction {
    static selector = ".o_mail_group";
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                "o_has_error": this.inError,
            }),
        },
        ".form-control, .form-select": {
            "t-att-class": () => ({
                "is-invalid": this.inError,
            }),
        },
        ".o_mg_subscribe_btn": {
            "t-on-click.prevent": this.onToggleSubscribe,
            "t-att-class": () => ({
                "btn-primary": !this.isMember,
                "btn-outline-primary": this.isMember,
            }),
            "t-out": () => this.isMember ? _t('Unsubscribe') : _t('Subscribe'),
        },
    };

    setup() {
        this.inError = false;
        this.mailgroupId = this.el.dataset.id;
        this.isMember = this.el.dataset.isMember || false;
        const searchParams = (new URL(document.location.href)).searchParams;
        this.token = searchParams.get('token');
        this.forceUnsubscribe = searchParams.has('unsubscribe');
    }

    async onToggleSubscribe() {
        const email = this.el.querySelector(".o_mg_subscribe_email").value;

        if (!email.match(/.+@.+/)) {
            this.inError = true;
            return false;
        }
        this.inError = false;

        const action = (this.isMember || this.forceUnsubscribe) ? 'unsubscribe' : 'subscribe';
        const response = await this.waitFor(rpc('/group/' + action, {
            'group_id': this.mailgroupId,
            'email': email,
            'token': this.token,
        }));

        this.el.querySelector(".o_mg_alert")?.remove();

        if (response === 'added') {
            this.isMember = true;
        } else if (response === 'removed') {
            this.isMember = false;
        } else if (response === 'email_sent') {
            this.el.innerHTML = `<div class="o_mg_alert alert alert-success" role="alert"/>${_t('An email with instructions has been sent.')}</div>`;
        } else if (response === 'is_already_member') {
            this.isMember = true;
            const divEl = document.createElement("div");
            divEl.classList.add("o_mg_alert alert alert-warning");
            divEl.setAttribute("role", "alert");
            divEl.innerText = _t('This email is already subscribed.');
            this.insert(divEl, this.el.querySelector(".o_mg_subscribe_form"), "beforebegin")
        } else if (response === 'is_not_member') {
            if (!this.forceUnsubscribe) {
                this.isMember = false;
            }
            const divEl = document.createElement("div");
            divEl.classList.add("o_mg_alert alert alert-warning");
            divEl.setAttribute("role", "alert");
            divEl.innerText = _t('This email is not subscribed.');
            this.insert(divEl, this.el.querySelector(".o_mg_subscribe_form"), "beforebegin")
        }
    }
}

registry
    .category("public.interactions")
    .add("mail_group.mail_group", MailGroup);
