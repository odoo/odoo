import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class MailGroup extends Interaction {
    static selector = ".o_mail_group";
    dynamicContent = {
        _root: {
            "t-att-class": () => ({ "o_has_error": this.inError }),
        },
        ".form-control, .form-select": {
            "t-att-class": () => ({ "is-invalid": this.inError }),
        },
        ".o_mg_subscribe_btn": {
            "t-on-click.prevent": this.onToggleSubscribeClick,
        },
        ".o_mg_email_input_group": {
            "t-att-class": () => ({ "d-none": this.isMember }),
        },
        ".o_mg_unsubscribe_btn": {
            "t-att-class": () => ({ "d-none": !this.isMember }),
        },
    };

    setup() {
        this.inError = false;
        this.form = this.el.querySelector(".o_mg_subscribe_form");
        this.membersCountEl = this.el.querySelector(".o_mg_members_count");
        this.mailGroupId = this.el.dataset.id;
        this.isMember = this.el.dataset.isMember || false;
        const searchParams = (new URL(document.location.href)).searchParams;
        this.token = searchParams.get("token");
        this.forceUnsubscribe = searchParams.has("unsubscribe");
    }

    _displayAlert(textContent, classes){
        const alert = document.createElement("div");
        alert.setAttribute("class", `o_mg_alert alert ${classes}`);
        alert.setAttribute("role", "alert");
        alert.textContent = textContent;
        this.insert(alert, this.form, "beforebegin");
    }

    async onToggleSubscribeClick() {
        const email = this.el.querySelector(".o_mg_subscribe_email").value;

        if (!email.match(/.+@.+/)) {
            this.inError = true;
            return false;
        }
        this.inError = false;

        const action = (this.isMember || this.forceUnsubscribe) ? "unsubscribe" : "subscribe";
        const response = await this.waitFor(rpc("/group/" + action, {
            "group_id": this.mailGroupId,
            "email": email,
            "token": this.token,
        }));

        this.el.querySelector(".o_mg_alert")?.remove();

        if (this.membersCountEl && ["added", "removed"].includes(response)) {
            const membersCount = parseInt(this.membersCountEl.textContent) || 0;
            this.membersCountEl.textContent = Math.max(response === "added" ? membersCount + 1 : membersCount - 1, 0);
        }

        if (response === "added") {
            this.isMember = true;
        } else if (response === "removed") {
            this.isMember = false;
        } else if (response === "email_sent") {
            this._displayAlert(_t("An email with instructions has been sent."), "alert-success");
        } else if (response === "is_already_member") {
            this.isMember = true;
            this._displayAlert(_t("This email is already subscribed."), "alert-warning");
        } else if (response === "is_not_member") {
            if (!this.forceUnsubscribe) {
                this.isMember = false;
            }
            this._displayAlert(_t("This email is not subscribed."), "alert-warning");
        }
    }
}

registry
    .category("public.interactions")
    .add("mail_group.mail_group", MailGroup);
