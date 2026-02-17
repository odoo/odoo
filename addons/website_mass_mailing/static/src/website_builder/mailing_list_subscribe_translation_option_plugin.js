import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ToggleThanksMessageAction } from "./mailing_list_subscribe_option_plugin";

export class ToggleThanksMessageTranslationOption extends BaseOptionComponent {
    static id = "toggle_thanks_message_translation_option"
    static template = "website_mass_mailing.ToggleThanksMessageTranslationOption";

    static hideOverlay = false;
}

registry.category("website-options").add(ToggleThanksMessageTranslationOption.id, ToggleThanksMessageTranslationOption);

export class MailingListSubscribeTranslationOptionPlugin extends Plugin {
    static id = "newsletterSubscribeCommonOptionTranslation";
    resources = {
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
