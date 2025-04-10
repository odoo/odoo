/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = publicWidget.Widget.extend({

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
        this.notification = this.bindService("notification");
        // dynamic get rather than import as we don't depend on this module
        if (session.turnstile_site_key) {
            const { turnStile } = odoo.loader.modules.get("@website_cf_turnstile/js/turnstile");
            this._turnstile = turnStile;
        }
    },

    /**
     * @override
     */
    willStart: async function () {
        this._recaptcha.loadLibs();
        return this._super(...arguments);
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        const post = this._getPost();
        const noTicketsOrdered = Object.values(post).map((value) => parseInt(value)).every(value => value === 0);
        var res = this._super.apply(this.arguments).then(function () {
            self.__onClick = self._onClick.bind(self);
            self.submitButtonEl = document.querySelector("#registration_form .a-submit");
            self.submitButtonEl.addEventListener("click", self.__onClick);
            self.submitButtonEl.disabled = noTicketsOrdered;
        });
        return res;
    },

    destroy() {
        this.submitButtonEl.removeEventListener("click", this.__onClick);
        this._super(...arguments);
    },

    _getPost: function () {
        var post = {};
        const selectEls = document.querySelectorAll("#registration_form select");
        selectEls.forEach(function (selectEl) {
            post[selectEl.name] = selectEl.value;
        });
        return post;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    async _onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const formEl = ev.currentTarget.closest("form");
        const buttonEl = ev.currentTarget.closest("[type='submit']");
        const post = this._getPost();
        buttonEl.disabled = true;
        const [modal, recaptchaToken] = await Promise.all([
            rpc(formEl.action, post),
            this._recaptcha.getToken("website_event_registration"),
        ]);
        if (recaptchaToken.error) {
            this.notification.add(recaptchaToken.error, {
                type: "danger",
                title: _t("Error"),
                sticky: true,
            });
            buttonEl.disabled = false;
            return false;
        }
        const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
        const form = modalEl.querySelector("form#attendee_registration");
        const _onClick = () => {
            buttonEl.disabled = false;
            modalEl.querySelector(".js_goto_event").removeEventListener("click", _onClick);
            modalEl.querySelector(".btn-close").removeEventListener("click", _onClick);
            modalEl.remove();
        };
        modalEl.querySelector(".js_goto_event").addEventListener("click", _onClick);
        modalEl.querySelector(".btn-close").addEventListener("click", _onClick);
        modalEl.querySelector("form").addEventListener("submit", (ev) => {
            const tokenInput = document.createElement("input");
            tokenInput.setAttribute("name", "recaptcha_token_response");
            tokenInput.setAttribute("type", "hidden");
            tokenInput.setAttribute("value", recaptchaToken.token);
            ev.currentTarget.appendChild(tokenInput);
        });
        // the turnstile container needs to be already appended to the dom before rendering
        // see modal.js for events
        modalEl.addEventListener("shown.bs.modal", () => {
            this._addTurnstile(form);
        });
        const formModal = Modal.getOrCreateInstance(modalEl, {
            backdrop: "static",
            keyboard: false,
        });
        formModal.show();
    },

    _addTurnstile: function (form) {
        if (!this._turnstile) {
            return false;
        }

        const turnstileNodes = this._turnstile.addTurnstile("website_event_registration");

        const modalFooter = form.querySelector("div.modal-footer");
        const formButton = form.querySelector("button[type=submit]");

        this._turnstile.addSpinnerNoMangle(formButton);
        turnstileNodes.prependTo(modalFooter);
        this._turnstile.renderTurnstile(turnstileNodes);

        return true;
    },
});

publicWidget.registry.EventRegistrationFormInstance = publicWidget.Widget.extend({
    selector: '#registration_form',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.instance = new EventRegistrationForm(this);
        return Promise.all([def, this.instance.attachTo(this.el)]);
    },
    /**
     * @override
     */
    destroy: function () {
        this.instance.setElement(null);
        this._super.apply(this, arguments);
        this.instance.setElement(this.el);
    },
});

publicWidget.registry.EventPage = publicWidget.Widget.extend({
    selector: '#o_wevent_event_submenu .dropdown-menu a.dropdown-toggle',
    events: {
        'click ': '_onClickSubDropDown',
    },
    _onClickSubDropDown:function(ev){
        ev.stopPropagation()
    }
})

export default EventRegistrationForm;
