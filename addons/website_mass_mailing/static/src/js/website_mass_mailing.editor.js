odoo.define('website_mass_mailing.editor', function (require) {
'use strict';

var core = require('web.core');
const Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');

const qweb = core.qweb;
var _t = core._t;


options.registry.mailing_list_subscribe = options.Class.extend({
    /**
     * @override
     */
    onBuilt() {
        this._super(...arguments);
        if (this.mailingLists.length) {
            this.$target.attr("data-list-id", this.mailingLists[0][0]);
        } else {
            Dialog.confirm(this, _t("No mailing list found, do you want to create a new one? This will save all your changes, are you sure you want to proceed?"), {
                confirm_callback: () => {
                    this.trigger_up('request_save', {
                        reload: false,
                        onSuccess: () => {
                            window.location.href = '/web#action=mass_mailing.action_view_mass_mailing_lists';
                        },
                    });
                },
                cancel_callback: () => {
                    this.trigger_up('remove_snippet', {
                        $snippet: this.$target,
                    });
                },
            });
        }
    },
    /**
     * @override
     */
    cleanForSave() {
        const previewClasses = ['o_disable_preview', 'o_enable_preview'];
        const toCleanElsSelector =
            ".js_subscribe_btn, .js_subscribed_btn, #newsletter_form, .s_website_form_end_message";
        const toCleanEls = this.$target[0].querySelectorAll(toCleanElsSelector);
        toCleanEls.forEach(element => {
            element.classList.remove(...previewClasses);
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    toggleThanksButton(previewMode, widgetValue, params) {
        const toSubscribeEl = this.$target[0].querySelector(".js_subscribe_btn, #newsletter_form");
        const thanksMessageEl =
            this.$target[0].querySelector(".js_subscribed_btn, .s_website_form_end_message");

        thanksMessageEl.classList.toggle("o_disable_preview", !widgetValue);
        thanksMessageEl.classList.toggle("o_enable_preview", widgetValue);
        toSubscribeEl.classList.toggle("o_enable_preview", !widgetValue);
        toSubscribeEl.classList.toggle("o_disable_preview", widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName !== 'toggleThanksButton') {
            return this._super(...arguments);
        }
        const toSubscribeElSelector =
            ".js_subscribe_btn.o_disable_preview, #newsletter_form.o_disable_preview";
        return this.$target[0].querySelector(toSubscribeElSelector) ? "true" : "";
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        this.mailingLists = await this._rpc({
            model: 'mailing.list',
            method: 'name_search',
            args: ['', [['is_public', '=', true]]],
            context: this.options.recordInfo.context,
        });
        if (this.mailingLists.length) {
            const selectEl = uiFragment.querySelector('we-select[data-attribute-name="listId"]');
            for (const mailingList of this.mailingLists) {
                const button = document.createElement('we-button');
                button.dataset.selectDataAttribute = mailingList[0];
                button.textContent = mailingList[1];
                selectEl.appendChild(button);
            }
        }
        const checkboxEl = document.createElement('we-checkbox');
        checkboxEl.setAttribute('string', _t("Display Thanks Button"));
        checkboxEl.dataset.toggleThanksButton = 'true';
        checkboxEl.dataset.noPreview = 'true';
        checkboxEl.dataset.dependencies = "!form_opt";
        uiFragment.appendChild(checkboxEl);
    },
});

options.registry.recaptchaSubscribe = options.Class.extend({
    /**
     * Toggle the recaptcha legal terms
     */
    toggleRecaptchaLegal: function (previewMode, value, params) {
        const recaptchaLegalEl = this.$target[0].querySelector('.o_recaptcha_legal_terms');
        if (recaptchaLegalEl) {
            recaptchaLegalEl.remove();
        } else {
            const template = document.createElement('template');
            template.innerHTML = qweb.render("google_recaptcha.recaptcha_legal_terms");
            this.$target[0].appendChild(template.content.firstElementChild);
        }
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'toggleRecaptchaLegal':
                return !this.$target[0].querySelector('.o_recaptcha_legal_terms') || '';
        }
        return this._super(...arguments);
    },
});
});
