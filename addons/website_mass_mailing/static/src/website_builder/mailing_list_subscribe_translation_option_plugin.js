import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ToggleThanksMessageAction } from "./mailing_list_subscribe_option_plugin";

const selector = ".s_newsletter_list";
const exclude = [
    ".s_newsletter_block .s_newsletter_list",
    ".o_newsletter_popup .s_newsletter_list",
    ".s_newsletter_box .s_newsletter_list",
    ".s_newsletter_centered .s_newsletter_list",
    ".s_newsletter_grid .s_newsletter_list",
].join(", ");

export class ToggleThanksMessageBlockOption extends BaseOptionComponent {
    static template = "website_mass_mailing.ToggleThanksMessageTranslationOption";
    static selector = selector;
    static exclude = exclude;
    static hideOverlay = false;
    static editableOnly = false;
    static title = _t("Newsletter block");
}

export class ToggleThanksMessagePopupOption extends ToggleThanksMessageBlockOption {
    static selector = ".o_newsletter_popup";
    static exclude = "";
    static applyTo = ".o_newsletter_popup .s_newsletter_list";
    static title = _t("Newsletter popup");
}

export class MailingListSubscribeTranslationOptionPlugin extends Plugin {
    static id = "newsletterSubscribeCommonOptionTranslation";
    resources = {
        builder_options: [ToggleThanksMessageBlockOption, ToggleThanksMessagePopupOption],
        builder_actions: {
            ToggleThanksMessageAction,
        },
    };
}

registry
    .category("translation-plugins")
    .add(
        MailingListSubscribeTranslationOptionPlugin.id,
        MailingListSubscribeTranslationOptionPlugin
    );
