import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { RecaptchaSubscribeOption } from "./recaptcha_subscribe_option";
import { renderToElement } from "@web/core/utils/render";

class RecaptchaSubscribeOptionPlugin extends Plugin {
    static id = "recaptchaSubscribeOption";
    static dependencies = ["websiteSession"];

    resources = {
        builder_options: [
            {
                OptionComponent: RecaptchaSubscribeOption,
                props: { hasRecaptcha: this.hasRecaptcha.bind(this) },
                selector: ".s_newsletter_list",
                exclude:
                    ".s_newsletter_block .s_newsletter_list, .o_newsletter_popup .s_newsletter_list, .s_newsletter_box .s_newsletter_list, .s_newsletter_centered .s_newsletter_list, .s_newsletter_grid .s_newsletter_list",
            },
            {
                OptionComponent: RecaptchaSubscribeOption,
                props: { hasRecaptcha: this.hasRecaptcha.bind(this) },
                selector: ".o_newsletter_popup",
                applyTo: ".s_newsletter_list",
            },
        ],
        builder_actions: [
            {
                toggleRecaptchaLegal: {
                    apply: ({ editingElement }) => {
                        const template = document.createElement("template");
                        template.content.append(
                            renderToElement("google_recaptcha.recaptcha_legal_terms")
                        );
                        editingElement.appendChild(template.content.firstElementChild);
                    },
                    clean: ({ editingElement }) => {
                        editingElement.querySelector(".o_recaptcha_legal_terms").remove();
                    },
                },
            },
        ],
    };

    hasRecaptcha() {
        return !!this.dependencies.websiteSession.getSession().recaptcha_public_key;
    }
}

registry
    .category("website-plugins")
    .add(RecaptchaSubscribeOptionPlugin.id, RecaptchaSubscribeOptionPlugin);
