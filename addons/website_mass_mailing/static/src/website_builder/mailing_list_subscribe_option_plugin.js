import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import {  NewsletterSubscribeCommonOptionBase } from "./newsletter_subscribe_common_option";
import { getElementsWithOption, filterExtends } from "@html_builder/utils/utils";
import { BuilderAction } from "@html_builder/core/builder_action";

class MailingListSubscribeOptionPlugin extends Plugin {
    static id = "mailingListSubscribeOption";
    static dependencies = ["savePlugin"];
    static shared = ["fetchMailingLists"];
    resources = {
        builder_actions: {
            ToggleThanksMessageAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.newsletterOptions = filterExtends(
            this.getResource("builder_options"),
            NewsletterSubscribeCommonOptionBase,
        );
    }

    async onSnippetDropped({ snippetEl }) {
        const newsLetterEls = [];
        for (const { selector, exclude, applyTo } of this.newsletterOptions) {
            newsLetterEls.push(...getElementsWithOption(snippetEl, selector, exclude, applyTo));
        }
        if (!newsLetterEls.length) {
            return;
        }

        await this.fetchMailingLists();
        if (!this.mailingLists.length) {
            let cancelDrop = false;
            await new Promise((resolve) => {
                this.services.dialog.add(ConfirmationDialog, {
                    body: _t(
                        "No mailing list found, do you want to create a new one? This will save all your changes, are you sure you want to proceed?"
                    ),
                    confirm: async () => {
                        // TODO properly save and redirect.
                        await this.dependencies.savePlugin.save();
                        window.location.href =
                            "/odoo/action-mass_mailing.action_view_mass_mailing_lists";
                    },
                    cancel: () => cancelDrop = true,
                }, { onClose: resolve });
            })
            // Cancel the drop if the dialog was cancelled.
            if (cancelDrop) {
                return true;
            }
        } else {
            for (const newsLetterEl of newsLetterEls) {
                newsLetterEl.dataset.listId = this.mailingLists[0].id;
            }
        }
    }

    async fetchMailingLists() {
        if (!this.mailingLists) {
            const context = Object.assign({}, user.context, {
                website_id: this.services.website.currentWebsite.id,
                lang: this.services.website.currentWebsite.metadata.lang,
                user_lang: user.context.lang,
            });
            const response = await this.services.orm.call(
                "mailing.list",
                "name_search",
                ["", [["is_public", "=", true]]],
                { context }
            );
            this.mailingLists = [];
            for (const entry of response) {
                this.mailingLists.push({ id: entry[0], name: entry[1] });
            }
        }
        return this.mailingLists;
    }

    cleanForSave({ root }) {
        const newsLetterEls = [];
        for (const { selector, exclude, applyTo } of this.newsletterOptions) {
            newsLetterEls.push(...getElementsWithOption(root, selector, exclude, applyTo));
        }
        for (const newsLetterEl of newsLetterEls) {
            this.removePreview(newsLetterEl);
        }
    }

    removePreview(editingElement) {
        const previewClasses = ["o_disable_preview", "o_enable_preview"];
        const toCleanElsSelector = ".js_subscribe_wrap, .js_subscribed_wrap";
        const toCleanEls = editingElement.querySelectorAll(toCleanElsSelector);
        for (const toCleanEl of toCleanEls) {
            toCleanEl.classList.remove(...previewClasses);
        }
    }
}

export class ToggleThanksMessageAction extends BuilderAction {
    static id = "toggleThanksMessage";
    apply({ editingElement }) {
        this.setThanksMessageVisibility(editingElement, true);
    }
    clean({ editingElement }) {
        this.setThanksMessageVisibility(editingElement, false);
    }
    isApplied({ editingElement }) {
        return editingElement.querySelector(".js_subscribed_wrap")?.classList.contains("o_enable_preview");
    }
    setThanksMessageVisibility(editingElement, isVisible) {
        const toSubscribeEl = editingElement.querySelector(".js_subscribe_wrap");
        const thanksMessageEl = editingElement.querySelector(".js_subscribed_wrap");
        thanksMessageEl.classList.toggle("o_enable_preview", isVisible);
        thanksMessageEl.classList.toggle("o_disable_preview", !isVisible);
        toSubscribeEl.classList.toggle("o_enable_preview", !isVisible);
        toSubscribeEl.classList.toggle("o_disable_preview", isVisible);
    }
}

registry
    .category("website-plugins")
    .add(MailingListSubscribeOptionPlugin.id, MailingListSubscribeOptionPlugin);
