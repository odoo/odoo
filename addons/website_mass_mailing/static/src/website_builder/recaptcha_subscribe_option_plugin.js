import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class RecaptchaSubscribeOptionPlugin extends Plugin {
    static id = "recaptchaSubscribeOption";
    static dependencies = ["websiteBridge"];
    static shared = ["hasRecaptcha"];
    resources = {
        builder_actions: {
            ToggleRecaptchaLegalAction,
        }
    };

    hasRecaptcha() {
        return !!this.dependencies.websiteBridge.getSession().recaptcha_public_key;
    }
}

export class ToggleRecaptchaLegalAction extends BuilderAction {
    static id = "toggleRecaptchaLegal";
    static dependencies = ["websiteBridge"];
    apply({ editingElement }) {
        editingElement.appendChild(
            this.dependencies.websiteBridge.renderToElement(
                "google_recaptcha.recaptcha_legal_terms"
            )
        );
    }
    clean({ editingElement }) {
        editingElement.querySelector(".o_recaptcha_legal_terms").remove();
    }
}

registry
    .category("website-plugins")
    .add(RecaptchaSubscribeOptionPlugin.id, RecaptchaSubscribeOptionPlugin);
