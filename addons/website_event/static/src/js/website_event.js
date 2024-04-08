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
            var submitButton = document.querySelector('#registration_form .a-submit');
            submitButton.removeEventListener('click', self.on_click);
            submitButton.addEventListener('click', function (ev) {
                self.on_click(ev);
            });
            submitButton.disabled = noTicketsOrdered;
        });
        return res;
    },

    _getPost: function () {
        var post = {};
        var selects = document.querySelectorAll('#registration_form select');
        selects.forEach(function (select) {
            post[select.name] = select.value;
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
        var form = ev.currentTarget.closest('form');
        var button = ev.currentTarget.closest('[type="submit"]');
        const post = this._getPost();
        button.disabled = true;
        return rpc(form.action, post).then(function (modal) {
            var modalElement = document.createElement('div');
            modalElement.innerHTML = modal;
            modalElement.querySelector('.modal-body > div').classList.remove('container'); // retrocompatibility - REMOVE ME in master / saas-19
            modalElement.querySelector('.modal-body').appendChild(modalElement);
            const modalBS = new Modal(modalElement, {backdrop: 'static', keyboard: false});
            modalBS.show();
            modalElement.querySelector('.js_goto_event').addEventListener('click', function () {
                modalBS.hide();
                button.disabled = false;
            });
            modalElement.querySelector('.btn-close').addEventListener('click', function () {
                button.disabled = false;
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
