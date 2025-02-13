/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { jsonrpc } from "@web/core/network/rpc_service";
import { renderToElement } from "@web/core/utils/render";
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
            const form = $modal[0].querySelector("form#attendee_registration");
            self._addTurnstile(form);
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

    _addTurnstile: function (form) {
        if (!session.turnstile_site_key) {
            return false;
        }
        this._removeTurnstile();

        const formButton = form.querySelector("button[type=submit]")
        formButton.setAttribute("disabled", "1")
        const globalCallbackName = "websiteEventRegistrationFormTurnstileExecuteCallback"
        globalThis[globalCallbackName] = () => formButton.removeAttribute("disabled");

        const turnstileContainer = renderToElement("website_cf_turnstile.turnstile_container", {
            action: "website_event_registration",
            additionalClasses: "float-end s_turnstile_container",
            executeGlobalCallback: globalCallbackName,
            errorGlobalCallback: globalCallbackName,
            sitekey: session.turnstile_site_key,
        });

        const modalFooter = form.querySelector("div.modal-footer");
        modalFooter.prepend(turnstileContainer);
        
        // script will implicitly render inside all cf-turnstile containers when loaded
        if (!("turnstile" in window)) {
            const turnstileScript = renderToElement("website_cf_turnstile.turnstile_remote_script");
            document.body.appendChild(turnstileScript);
        } else {
            window.turnstile.render(turnstileContainer);
        }

        return true;
    },
    _removeTurnstile: function () {
        document.querySelectorAll(".s_turnstile_container").forEach(e => e.remove());
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
