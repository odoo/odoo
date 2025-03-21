import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { NewsletterSubscribeCommonOption } from "./newsletter_subscribe_common_option";
import { getSelectorParams } from "@html_builder/utils/utils";
import {
    applyFunDependOnSelectorAndExclude,
    applyAsyncFunDependOnSelectorAndExclude,
} from "@html_builder/plugins/utils";

class MailingListSubscribeOptionPlugin extends Plugin {
    static id = "mailingListSubscribeOption";
    static dependencies = ["remove", "savePlugin"];
    static shared = ["fetchMailingLists"];
    resources = {
        builder_actions: [
            {
                toggleThanksMessage: {
                    apply: ({ editingElement }) => {
                        this.setThanksMessageVisibility(editingElement, true);
                    },
                    clean: ({ editingElement }) => {
                        this.setThanksMessageVisibility(editingElement, false);
                    },
                    isApplied: ({ editingElement }) =>
                        editingElement
                            .querySelector(".js_subscribed_wrap")
                            .classList.contains("o_enable_preview"),
                },
            },
        ],
        on_add_element_handlers: this.onAddElement.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.mailingListSubscribeOptionSelectorParams = getSelectorParams(
            this.getResource("builder_options"),
            NewsletterSubscribeCommonOption
        );
    }

    setThanksMessageVisibility(editingElement, isVisible) {
        const toSubscribeEl = editingElement.querySelector(".js_subscribe_wrap");
        const thanksMessageEl = editingElement.querySelector(".js_subscribed_wrap");
        thanksMessageEl.classList.toggle("o_enable_preview", isVisible);
        thanksMessageEl.classList.toggle("o_disable_preview", !isVisible);
        toSubscribeEl.classList.toggle("o_enable_preview", !isVisible);
        toSubscribeEl.classList.toggle("o_disable_preview", isVisible);
    }

    async onAddElement({ elementToAdd }) {
        const proms = [];
        for (const mailingListSubscribeOptionSelector of this
            .mailingListSubscribeOptionSelectorParams) {
            proms.push(
                applyAsyncFunDependOnSelectorAndExclude(
                    this.addNewsletterListElement.bind(this),
                    elementToAdd,
                    mailingListSubscribeOptionSelector
                )
            );
        }
        await Promise.all(proms);
    }

    async addNewsletterListElement(elementToAdd) {
        await this.fetchMailingLists();
        if (this.mailingLists.length) {
            elementToAdd.dataset.listId = this.mailingLists[0].id;
        } else {
            this.services.dialog.add(ConfirmationDialog, {
                body: _t(
                    "No mailing list found, do you want to create a new one? This will save all your changes, are you sure you want to proceed?"
                ),
                confirm: async () => {
                    await this.dependencies.savePlugin.save();
                    window.location.href =
                        "/odoo/action-mass_mailing.action_view_mass_mailing_lists";
                },
                cancel: () => {
                    this.dependencies.remove.removeElement(elementToAdd);
                },
            });
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
        for (const mailingListSubscribeOptionSelector of this
            .mailingListSubscribeOptionSelectorParams) {
            applyFunDependOnSelectorAndExclude(
                this.removePreview.bind(this),
                root,
                mailingListSubscribeOptionSelector
            );
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

registry
    .category("website-plugins")
    .add(MailingListSubscribeOptionPlugin.id, MailingListSubscribeOptionPlugin);
