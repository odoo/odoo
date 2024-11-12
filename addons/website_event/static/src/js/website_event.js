/** @odoo-module **/

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
    _onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const formEl = ev.currentTarget.closest("form");
        const buttonEl = ev.currentTarget.closest("[type='submit']");
        const post = this._getPost();
<<<<<<< 18.0
        buttonEl.disabled = true;
        return rpc(formEl.action, post).then((modal) => {
            const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
            const _onClick = () => {
                buttonEl.disabled = false;
                modalEl.querySelector(".js_goto_event").removeEventListener("click", _onClick);
                modalEl.querySelector(".btn-close").removeEventListener("click", _onClick);
                modalEl.remove();
            };
            modalEl.querySelector(".js_goto_event").addEventListener("click", _onClick);
            modalEl.querySelector(".btn-close").addEventListener("click", _onClick);
            const formModal = Modal.getOrCreateInstance(modalEl, {
                backdrop: "static",
                keyboard: false,
||||||| 20e36f91c7de1ff0eb7370fa780a69872ee54485
        $button.attr('disabled', true);
        return rpc($form.attr('action'), post).then(function (modal) {
            var $modal = $(modal);
            $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
            $modal.appendTo(document.body);
            const modalBS = new Modal($modal[0], {backdrop: 'static', keyboard: false});
            modalBS.show();
            $modal.appendTo('body').modal('show');
            $modal.on('click', '.js_goto_event', function () {
                $modal.modal('hide');
                $button.prop('disabled', false);
            });
            $modal.on('click', '.btn-close', function () {
                $button.prop('disabled', false);
=======
        $button.attr('disabled', true);
        const self = this;
        return rpc($form.attr('action'), post).then(async function (modal) {
            const tokenObj = await self._recaptcha.getToken('website_event_registration');
            if (tokenObj.error) {
                self.notification.add(tokenObj.error, {
                    type: "danger",
                    title: _t("Error"),
                    sticky: true,
                });
                $button.prop('disabled', false);
                return false;
            }
            var $modal = $(modal);
            $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
            $modal.appendTo(document.body);
            const modalBS = new Modal($modal[0], {backdrop: 'static', keyboard: false});
            modalBS.show();
            $modal.appendTo('body').modal('show');
            $modal.on('click', '.js_goto_event', function () {
                $modal.modal('hide');
                $button.prop('disabled', false);
            });
            $modal.on('click', '.btn-close', function () {
                $button.prop('disabled', false);
>>>>>>> d29f13b0776624dbf7e63feda7a60f5d128eab28
            });
<<<<<<< 18.0
            formModal.show();
||||||| 20e36f91c7de1ff0eb7370fa780a69872ee54485
=======
            $modal.on('submit', 'form', function (ev) {
                const tokenInput = document.createElement('input');
                tokenInput.setAttribute('name', 'recaptcha_token_response');
                tokenInput.setAttribute('type', 'hidden');
                tokenInput.setAttribute('value', tokenObj.token);
                ev.currentTarget.appendChild(tokenInput);
            })
>>>>>>> d29f13b0776624dbf7e63feda7a60f5d128eab28
        });
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
