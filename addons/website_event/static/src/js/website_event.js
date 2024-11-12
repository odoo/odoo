/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { jsonrpc } from "@web/core/network/rpc_service";

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
            $('#registration_form .a-submit')
                .off('click')
                .click(function (ev) {
                    self.on_click(ev);
                })
                .prop('disabled', noTicketsOrdered);
        });
        return res;
    },

    _getPost: function () {
        var post = {};
        $('#registration_form select').each(function () {
            post[$(this).attr('name')] = $(this).val();
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
        var $form = $(ev.currentTarget).closest('form');
        var $button = $(ev.currentTarget).closest('[type="submit"]');
        const post = this._getPost();
        $button.attr('disabled', true);
        const self = this;
        return jsonrpc($form.attr('action'), post).then(async function (modal) {
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
            });
            $modal.on('submit', 'form', function (ev) {
                const tokenInput = document.createElement('input');
                tokenInput.setAttribute('name', 'recaptcha_token_response');
                tokenInput.setAttribute('type', 'hidden');
                tokenInput.setAttribute('value', tokenObj.token);
                ev.currentTarget.appendChild(tokenInput);
            })
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
        return Promise.all([def, this.instance.attachTo(this.$el)]);
    },
    /**
     * @override
     */
    destroy: function () {
        this.instance.setElement(null);
        this._super.apply(this, arguments);
        this.instance.setElement(this.$el);
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
