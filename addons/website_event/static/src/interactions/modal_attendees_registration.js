import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { rpc } from "@web/core/network/rpc";

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = publicWidget.Widget.extend({

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
        this.notification = this.bindService("notification");
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
        const formModal = Modal.getOrCreateInstance(modalEl, {
            backdrop: "static",
            keyboard: false,
        });
        formModal.show();
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

export default EventRegistrationForm;
