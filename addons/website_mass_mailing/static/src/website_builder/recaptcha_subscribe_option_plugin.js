import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

class RecaptchaSubscribeOptionPlugin extends Plugin {
    static id = "recaptchaSubscribeOption";
    static dependencies = ["websiteSession"];
    static shared = ["hasRecaptcha"];
    resources = {
        builder_actions: {
            ToggleRecaptchaLegalAction,
        }
    };

    hasRecaptcha() {
        return !!this.dependencies.websiteSession.getSession().recaptcha_public_key;
    }
}

export class ToggleRecaptchaLegalAction extends BuilderAction {
    static id = "toggleRecaptchaLegal";
    apply({ editingElement }) {
        const template = document.createElement("template");
        template.content.append(
            renderToElement("google_recaptcha.recaptcha_legal_terms")
        );
        editingElement.appendChild(template.content.firstElementChild);
    }
    clean({ editingElement }) {
        editingElement.querySelector(".o_recaptcha_legal_terms").remove();
    }
}

registry
    .category("website-plugins")
    .add(RecaptchaSubscribeOptionPlugin.id, RecaptchaSubscribeOptionPlugin);
