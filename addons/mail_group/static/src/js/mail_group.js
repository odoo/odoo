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
        this.form = this.el.querySelector(".o_mg_subscribe_form");
        this.membersCountEl = this.el.querySelector(".o_mg_members_count");
        this.mailGroupId = this.el.dataset.id;
        this.isMember = this.el.dataset.isMember || false;
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
    _toggleSubscribeButton: function(isSubscribe) {
        this.el.querySelector(".o_mg_email_input_group").classList.toggle("d-none", isSubscribe);
        this.el.querySelector(".o_mg_unsubscribe_btn").classList.toggle("d-none", !isSubscribe);
    },

    _updateMembersCount: function (action) {
        if (!["added", "removed"].includes(action)){
            return;
        }
        const membersCount = parseInt(this.membersCountEl.textContent) || 0;
        this.membersCountEl.textContent = Math.max(action === "added" ? membersCount + 1 : membersCount - 1, 0);
    },

    _generateAlert: function (textContent, classes) {
        const alert = document.createElement("div");
        alert.setAttribute("class", `o_mg_alert alert ${classes}`);
        alert.setAttribute("role", "alert");
        alert.textContent = textContent;
        return alert;
    },

    _displayAlert: function (alert){
        this.form.parentNode.insertBefore(
            alert,
            this.form
        );
    },

    _onSubscribeBtnClick: async function (ev) {
        ev.preventDefault();
        const email = this.el.querySelector(".o_mg_subscribe_email").value;

        if (!email.match(/.+@.+/)) {
            this.form.classList.add("o_has_error");
            this.form.querySelector(".form-control, .form-select").classList.add("is-invalid");
            return false;
        }

        this.form.classList.remove("o_has_error");
        this.form.querySelector(".form-control, .form-select").classList.remove("is-invalid");

        const action = (this.isMember || this.forceUnsubscribe) ? 'unsubscribe' : 'subscribe';

        const response = await rpc('/group/' + action, {
            'group_id': this.mailGroupId,
            'email': email,
            'token': this.token,
        });

        this.el.querySelector(".o_mg_alert")?.remove();

        if (this.membersCountEl) {
            this._updateMembersCount(response);
        }

        if (response === 'added') {
            this.isMember = true;
            this._toggleSubscribeButton(true);
        } else if (response === 'removed') {
            this.isMember = false;
            this._toggleSubscribeButton(false);
        } else if (response === 'email_sent') {
            // The confirmation email has been sent
            this.form.hidden = true;
            this._displayAlert(this._generateAlert(_t("An email with instructions has been sent."), "alert-success"));
        } else if (response === 'is_already_member') {
            this.isMember = true;
            this._toggleSubscribeButton(true);
            this._displayAlert(this._generateAlert(_t("This email is already subscribed."), "alert-warning"));
        } else if (response === 'is_not_member') {
            if (!this.forceUnsubscribe) {
                this.isMember = false;
                this._toggleSubscribeButton(false);
            }
            this._displayAlert(this._generateAlert(_t("This email is not subscribed."), "alert-warning"));
        }

    },
});

export default publicWidget.registry.MailGroup;
