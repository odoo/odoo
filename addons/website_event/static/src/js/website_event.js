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
            });
            formModal.show();
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

publicWidget.registry.WebsiteEventLayout = publicWidget.Widget.extend({
    selector: '.o_wevent_index',
    disabledInEditableMode: false,
    events: {
        'change .o_wevent_apply_layout input': '_onApplyEventLayoutChange',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onApplyEventLayoutChange: async function (ev) {
        const wysiwyg = this.options.wysiwyg;
        if (wysiwyg) {
            wysiwyg.odooEditor.observerUnactive('_onApplyEventLayoutChange');
        }
        var clickedValue = ev.target.value;
        if (!this.editableMode) {
            await rpc('/event/save_event_layout_mode', {
                'layout_mode': clickedValue,
            });
        }

        // Update btn-group state
        document.querySelector('input.o_wevent_apply_grid').checked = (clickedValue === 'grid');
        document.querySelector('input.o_wevent_apply_list').checked = (clickedValue === 'list');
        document.querySelector('label.o_wevent_apply_grid').classList.toggle('active')
        document.querySelector('label.o_wevent_apply_list').classList.toggle('active')

        // Update layout
        document.querySelector('.o_wevent_event_grid_layout').classList.toggle('d-none');
        document.querySelector('.o_wevent_event_list_layout').classList.toggle('d-none');

        if (wysiwyg) {
            wysiwyg.odooEditor.observerActive('_onApplyEventLayoutChange');
        }
    },
});

export default {
    EventRegistrationForm,
    WebsiteEventLayout: publicWidget.registry.WebsiteEventLayout,
};
