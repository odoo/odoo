/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = publicWidget.Widget.extend({

    /**
     * @override
     */
    start: function () {
        var self = this;
        const post = this._getPost();
        const noTicketsOrdered = Object.values(post).map((value) => parseInt(value)).every(value => value === 0);
        var res = this._super.apply(this.arguments).then(function () {
            const submitButtonEl = document.querySelector("#registration_form .a-submit");
            submitButtonEl.removeEventListener("click", self.on_click);
            submitButtonEl.addEventListener("click", self.on_click.bind(self));
            submitButtonEl.disabled = noTicketsOrdered;
        });
        return res;
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
    on_click: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const formEl = ev.currentTarget.closest("form");
        const buttonEl = ev.currentTarget.closest("[type='submit']");
        const post = this._getPost();
        buttonEl.disabled = true;
        return rpc(formEl.action, post).then(function (modal) {
            const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
            modalEl.querySelector(".modal-body > div").classList.remove("container"); // retrocompatibility - REMOVE ME in master / saas-19
            document.body.append(modalEl);
            const formModal = Modal.getOrCreateInstance(modalEl, {
                backdrop: "static",
                keyboard: false,
            });
            formModal.show();
            modalEl.querySelector(".js_goto_event").addEventListener("click", function () {
                formModal.hide();
                buttonEl.disabled = false;
            });
            modalEl.querySelector(".btn-close").addEventListener("click", function () {
                buttonEl.disabled = false;
            });
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

export default EventRegistrationForm;
