import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TurnstileSubscribeOptionPlugin extends Plugin {
    static id = "turnstileSubscribeOption";
    static dependencies = ["websiteBridge"];
    static shared = ["hasTurnstile"];
    resources = {
        builder_actions: {
            ToggleTurnstileLegalAction,
        },
    };

    hasTurnstile() {
        return !!this.dependencies.websiteBridge.getSession().turnstile_site_key;
    }
}

export class ToggleTurnstileLegalAction extends BuilderAction {
    static id = "toggleTurnstileLegal";
    static dependencies = ["websiteBridge"];
    apply({ editingElement }) {
        editingElement.appendChild(
            this.dependencies.websiteBridge.renderToElement(
                "website_cf_turnstile.turnstile_legal_terms"
            )
        );
    }
    clean({ editingElement }) {
        editingElement.querySelector(".o_turnstile_legal_terms").remove();
    }
}

registry
    .category("website-plugins")
    .add(TurnstileSubscribeOptionPlugin.id, TurnstileSubscribeOptionPlugin);
