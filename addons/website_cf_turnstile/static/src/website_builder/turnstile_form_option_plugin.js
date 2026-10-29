import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TurnstileFormOptionPlugin extends Plugin {
    static id = "turnstileFormOption";
    static dependencies = ["websiteBridge"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            FormToggleTurnstileLegalAction,
        },
        builder_options_render_context: {
            hasTurnstileKey: !!this.dependencies.websiteBridge.getSession().turnstile_site_key,
        },
        content_editable_selectors: ".s_website_form form .s_website_form_turnstile",
        form_field_anchor_selectors: ".s_website_form_turnstile",
    };
}

export class FormToggleTurnstileLegalAction extends BuilderAction {
    static id = "formToggleTurnstileLegal";
    static dependencies = ["websiteBridge"];
    apply({ editingElement: el }) {
        const legalEl = this.dependencies.websiteBridge.renderToElement(
            "website_cf_turnstile.s_website_form_turnstile_legal"
        );
        legalEl.setAttribute("contentEditable", true);
        el.querySelector(".s_website_form_submit").insertAdjacentElement("beforebegin", legalEl);
    }
    clean({ editingElement: el }) {
        el.querySelector(".s_website_form_turnstile").remove();
    }
    isApplied({ editingElement: el }) {
        return !!el.querySelector(".s_website_form_turnstile");
    }
}

registry.category("website-plugins").add(TurnstileFormOptionPlugin.id, TurnstileFormOptionPlugin);
