import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { session } from "@web/session";
import {
    SelectTemplate,
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";


export class NewsletterBlock extends SelectTemplate {
    constructor() {
        super(...arguments);
        this.containerSelector = "> .container, > .container-fluid, > .o_container_small";
        this.selectTemplateWidgetName = "newsletter_template_opt";
    }
}

export class NewsletterMailingList extends SnippetOption {
    constructor() {
        super(...arguments);
        this.dialog = this.env.services.dialog;
        this.orm = this.env.services.orm;
        this.website = this.env.services.website;
    }

    /**
     * @override
     */
    async willStart() {
        await super.willStart();
        this.renderContext.recaptcha_public_key = session.recaptcha_public_key;
    }

    /**
     * @override
     */
    async onBuilt() {
        await super.onBuilt(...arguments);
        if (this.renderContext.mailingLists.length) {
            this.$target.attr("data-list-id", this.renderContext.mailingLists[0][0].toString());
        } else {
            this.dialog.add(ConfirmationDialog, {
                body: _t("No mailing list found, do you want to create a new one? This will save all your changes, are you sure you want to proceed?"),
                confirm: () => {
                    this.env.requestSave({
                        reload: false,
                        onSuccess: () => {
                            window.location.href =
                                "/odoo/action-mass_mailing.action_view_mass_mailing_lists";
                        },
                    });
                },
                cancel: () => {
                    this.env.removeSnippet({
                        $snippet: this.$target,
                    });
                },
            });
        }
    }
    /**
     * @override
     */
    async cleanForSave() {
        const previewClasses = ['o_disable_preview', 'o_enable_preview'];
        const toCleanElsSelector = ".js_subscribe_wrap, .js_subscribed_wrap";
        const toCleanEls = this.$target[0].querySelectorAll(toCleanElsSelector);
        toCleanEls.forEach(element => {
            element.classList.remove(...previewClasses);
        });
    }

    /**
     * @override
     */
    async _getRenderContext() {
        const mailingLists = await this.orm.call(
            "mailing.list",
            "name_search",
            ["", [["is_public", "=", true]]],
            { context: this.options.recordInfo.context }
        );
        return {
            ...super._getRenderContext(),
            mailingLists,
        };
    }

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
    }
    /**
     * Toggle the recaptcha legal terms
     */
    toggleRecaptchaLegal(previewMode, value, params) {
        const recaptchaLegalEl = this.$target[0].querySelector('.o_recaptcha_legal_terms');
        if (recaptchaLegalEl) {
            recaptchaLegalEl.remove();
        } else {
            const template = document.createElement('template');
            template.content.append(renderToElement("google_recaptcha.recaptcha_legal_terms"));
            this.$target[0].appendChild(template.content.firstElementChild);
        }
    }

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'toggleThanksMessage':
                return this.$target[0].querySelector(".js_subscribe_wrap.o_disable_preview") ? "true" : "";
            case 'toggleRecaptchaLegal':
                return !this.$target[0].querySelector('.o_recaptcha_legal_terms') || '';
        }
        return super._computeWidgetState(...arguments);
    }
}

registerWebsiteOption("NewsletterBlockTemplate", {
    Class: NewsletterBlock,
    template: "website_mass_mailing.s_newsletter_block_template_options",
    selector: ".s_newsletter_block",
});

registerWebsiteOption("NewsletterBlockMailingList", {
    Class: NewsletterMailingList,
    template: "website_mass_mailing.newsletter_mailing_list_options",
    selector: ".s_newsletter_block",
});
