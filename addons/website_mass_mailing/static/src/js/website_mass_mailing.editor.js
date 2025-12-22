/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import options from "@web_editor/js/editor/snippets.options";

options.registry.mailing_list_subscribe = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    onBuilt() {
        this._super(...arguments);
        if (this.mailingLists.length) {
            this.$target.attr("data-list-id", this.mailingLists[0][0]);
        } else {
            this.call("dialog", "add", ConfirmationDialog, {
                body: _t("No mailing list found, do you want to create a new one? This will save all your changes, are you sure you want to proceed?"),
                confirm: () => {
                    this.trigger_up("request_save", {
                        reload: false,
                        onSuccess: () => {
                            window.location.href =
                                "/odoo/action-mass_mailing.action_view_mass_mailing_lists";
                        },
                    });
                },
                cancel: () => {
                    this.trigger_up("remove_snippet", {
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
        const toCleanElsSelector = ".js_subscribe_wrap, .js_subscribed_wrap";
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
    toggleThanksMessage(previewMode, widgetValue, params) {
        const toSubscribeEl = this.$target[0].querySelector(".js_subscribe_wrap");
        const thanksMessageEl =
            this.$target[0].querySelector(".js_subscribed_wrap");

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
        if (methodName !== 'toggleThanksMessage') {
            return this._super(...arguments);
        }
        const toSubscribeElSelector = ".js_subscribe_wrap.o_disable_preview";
        return this.$target[0].querySelector(toSubscribeElSelector) ? "true" : "";
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        this.mailingLists = await this.orm.call(
            "mailing.list",
            "name_search",
            ["", [["is_public", "=", true]]],
            { context: this.options.recordInfo.context }
        );
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
        checkboxEl.setAttribute('string', _t("Display Thanks Message"));
        checkboxEl.dataset.toggleThanksMessage = 'true';
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
            template.content.append(renderToElement("google_recaptcha.recaptcha_legal_terms"));
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
